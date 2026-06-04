import json
import os
import shutil
import re
import uuid
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import delete, select, update

from config import PBIP_SCHEMA_URL, WORK_ROOT
from database import engine, init_db
from db_loader import DBLoader, DBReader
from extractors.report_extractor import ReportExtractor
from pbip_generator.report_writer import ReportWriter
from pbip_generator.model_writer import SemanticModelWriter
from services.utils import _safe_name
from schema import (
    canvas_pages,
    canvas_reports,
    canvas_visuals,
    semantic_model_files,
    semantic_models,
    visual_templates,
)


DEFAULT_CANVAS_WIDTH = 1280
DEFAULT_CANVAS_HEIGHT = 720
DEFAULT_GRID_COLUMNS = 12
DEFAULT_ROW_HEIGHT = 72


def _as_dict(value):
    return value.model_dump() if hasattr(value, "model_dump") else value


def _ensure_directory(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def _safe_write_json(path, payload):
    _ensure_directory(Path(path).parent)
    with open(path, "w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2, ensure_ascii=False)


def _safe_delete_path(path):
    p = Path(path)
    if p.is_dir():
        shutil.rmtree(p, ignore_errors=True)
    elif p.exists():
        p.unlink(missing_ok=True)


def _unzip_archive(archive_path, destination):
    destination_path = Path(destination).resolve()
    _ensure_directory(destination_path)
    with zipfile.ZipFile(archive_path, "r") as archive:
        for member in archive.infolist():
            member_path = destination_path / member.filename
            resolved = member_path.resolve()
            if destination_path not in resolved.parents and resolved != destination_path:
                raise ValueError(f"Archive contains an unsafe path: {member.filename}")
        archive.extractall(destination_path)


def _find_report_folder(root):
    root_path = Path(root)
    if not root_path.is_dir():
        return None
    for entry in root_path.iterdir():
        if entry.name.endswith(".Report") and entry.is_dir():
            return str(entry)
    return None


def _slugify(*parts):
    raw = "-".join(str(part).strip() for part in parts if part and str(part).strip())
    raw = raw.lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw)
    raw = raw.strip("-")
    return raw or uuid.uuid4().hex


def _first_number(*values, default):
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number is not None:
            return number
    return default


def _visual_type_from_payload(visual_json, fallback="unknown"):
    if not isinstance(visual_json, dict):
        return fallback
    return visual_json.get("visualType") or visual_json.get("visual_type") or fallback


def _slot_definitions_from_visual_json(visual_json):
    query_state = ((visual_json or {}).get("query") or {}).get("queryState") or {}
    projections = query_state.get("projections") or {}
    slot_definitions = []
    required_slots = []
    optional_slots = []

    for slot_key, projection_value in projections.items():
        items = projection_value if isinstance(projection_value, list) else [projection_value]
        normalized_items = [item for item in items if isinstance(item, dict) or isinstance(item, str)]
        sample = next((item for item in normalized_items if isinstance(item, dict)), {})
        field_type = sample.get("kind") or sample.get("fieldType") or sample.get("type") or "any"
        slot = {
            "name": slot_key,
            "role": slot_key,
            "field_type": field_type,
            "required": bool(normalized_items),
            "multi": len(normalized_items) > 1,
            "description": f"Imported PBIP slot for {slot_key}",
        }
        slot_definitions.append(slot)
        target = required_slots if slot["required"] else optional_slots
        target.append({"key": slot_key, "label": slot_key, "kind": field_type, "description": slot["description"]})

    return slot_definitions, required_slots, optional_slots


def _template_dimensions_from_visual_json(visual_json):
    position = (visual_json or {}).get("position") or {}
    width = int(round(_first_number(position.get("width"), default=3) / 100)) if position.get("width") else 3
    height = int(round(_first_number(position.get("height"), default=2) / 100)) if position.get("height") else 2
    return max(width, 1), max(height, 1)


def _build_template_payload(report_name, page_name, visual_name, visual_json, source_file):
    template_key = _slugify(report_name, page_name, visual_name, _visual_type_from_payload(visual_json))
    slot_definitions, required_slots, optional_slots = _slot_definitions_from_visual_json(visual_json)
    default_width, default_height = _template_dimensions_from_visual_json(visual_json)
    visual_type = _visual_type_from_payload(visual_json, template_key)
    default_format = deepcopy((visual_json or {}).get("config") or {})
    default_visual_json = deepcopy(visual_json or {})
    default_visual_json.setdefault("visualType", visual_type)
    default_visual_json.setdefault(
        "_templateSource",
        {
            "report": report_name,
            "page": page_name,
            "visual": visual_name,
            "source": source_file,
        },
    )
    return {
        "template_key": template_key,
        "name": visual_name or visual_type,
        "category": "Imported",
        "icon": None,
        "description": f"Imported from {source_file} on {page_name}.",
        "default_width": default_width,
        "default_height": default_height,
        "required_slots": required_slots,
        "optional_slots": optional_slots,
        "default_visual_json": default_visual_json,
        "visual_type": visual_type,
        "slot_definitions": slot_definitions,
        "default_format": default_format,
        "is_active": "1",
    }


def _write_project_files(output_root, file_rows):
    root_path = Path(output_root)
    for file_row in file_rows:
        relative_path = file_row["relative_path"]
        target_path = root_path.joinpath(*relative_path.split("/"))
        target_path.parent.mkdir(parents=True, exist_ok=True)

        content_kind = file_row["content_kind"]
        if content_kind == "json" and file_row["json_content"] is not None:
            with open(target_path, "w", encoding="utf-8") as fh:
                json.dump(file_row["json_content"], fh, indent=2, ensure_ascii=False)
        elif content_kind == "text" and file_row["text_content"] is not None:
            with open(target_path, "w", encoding="utf-8") as fh:
                fh.write(file_row["text_content"])
        elif content_kind == "binary" and file_row["binary_base64"] is not None:
            import base64

            with open(target_path, "wb") as fh:
                fh.write(base64.b64decode(file_row["binary_base64"]))


def _create_zip_archive(source_dir, target_zip_path):
    source_path = Path(source_dir)
    with zipfile.ZipFile(target_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zh:
        for file_path in source_path.rglob("*"):
            if file_path.is_file():
                zh.write(file_path, arcname=file_path.relative_to(source_path))


def _default_page_page_json(page_name, width, height):
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
        "name": page_name,
        "displayName": page_name,
        "displayOption": "FitToPage",
        "width": width,
        "height": height,
        "objects": {
            "outspacePane": [
                {
                    "properties": {
                        "width": {
                            "expr": {
                                "Literal": {
                                    "Value": "192L"
                                }
                            }
                        }
                    }
                }
            ]
        },
    }


def _default_report_json(report_settings, canvas_settings):
    theme_color = report_settings.get("themeColor") or "#154360"
    theme_name = report_settings.get("themeName") or "BIFoundryTheme"
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.2.0/schema.json",
        "themeCollection": {
            "baseTheme": {
                "name": theme_name,
                "type": "SharedResources",
                "reportVersionAtImport": {
                    "visual": "2.8.0",
                    "report": "3.2.0",
                    "page": "2.3.1",
                },
                "color": theme_color,
            }
        },
        "objects": {
            "section": [
                {
                    "properties": {
                        "verticalAlignment": {
                            "expr": {
                                "Literal": {
                                    "Value": "'Top'"
                                }
                            }
                        }
                    }
                }
            ]
        },
        "resourcePackages": [
            {
                "name": "SharedResources",
                "type": "SharedResources",
                "items": [
                    {
                        "name": theme_name,
                        "path": f"BaseThemes/{theme_name}.json",
                        "type": "BaseTheme",
                    }
                ],
            }
        ],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
            "useDefaultAggregateDisplayName": True,
            "canvas": {
                "width": canvas_settings.get("width", DEFAULT_CANVAS_WIDTH),
                "height": canvas_settings.get("height", DEFAULT_CANVAS_HEIGHT),
            },
        },
    }


def _default_visual_templates():
    def slot(name, role, field_type, required, multi=False, description=""):
        return {
            "name": name,
            "role": role,
            "field_type": field_type,
            "required": required,
            "multi": multi,
            "description": description,
        }

    return [
        {
            "template_key": "clusteredBarChart",
            "name": "Bar Chart",
            "visual_type": "clusteredBarChart",
            "slot_definitions": [
                slot("X Axis", "Category", "column", True, False, "Choose the category or axis column"),
                slot("Y Axis / Value", "Y", "measure", True, False, "Choose the measure to plot"),
                slot("Legend", "Legend", "column", False, False, "Optional legend grouping"),
                slot("Tooltip", "Tooltip", "any", False, False, "Optional tooltip fields"),
            ],
            "default_format": {},
            "is_active": "1",
            "category": "Chart",
            "icon": "bar_chart",
            "description": "Compare values across categories.",
            "default_width": 4,
            "default_height": 3,
            "required_slots": [
                {"key": "Category", "label": "Category", "kind": "column"},
                {"key": "Y", "label": "Y", "kind": "measure"},
            ],
            "optional_slots": [
                {"key": "Legend", "label": "Legend", "kind": "column"},
                {"key": "Tooltip", "label": "Tooltip", "kind": "any"},
            ],
            "default_visual_json": {"visualType": "clusteredBarChart"},
        },
        {
            "template_key": "clusteredColumnChart",
            "name": "Column Chart",
            "visual_type": "clusteredColumnChart",
            "slot_definitions": [
                slot("X Axis", "Category", "column", True, False, "Choose the category or axis column"),
                slot("Y Axis / Value", "Y", "measure", True, False, "Choose the measure to plot"),
                slot("Legend", "Legend", "column", False, False, "Optional legend grouping"),
                slot("Tooltip", "Tooltip", "any", False, False, "Optional tooltip fields"),
            ],
            "default_format": {},
            "is_active": "1",
            "category": "Chart",
            "icon": "bar_chart_3",
            "description": "Compare values across categories in columns.",
            "default_width": 4,
            "default_height": 3,
            "required_slots": [
                {"key": "Category", "label": "Category", "kind": "column"},
                {"key": "Y", "label": "Y", "kind": "measure"},
            ],
            "optional_slots": [
                {"key": "Legend", "label": "Legend", "kind": "column"},
                {"key": "Tooltip", "label": "Tooltip", "kind": "any"},
            ],
            "default_visual_json": {"visualType": "clusteredColumnChart"},
        },
        {
            "template_key": "lineChart",
            "name": "Line Chart",
            "visual_type": "lineChart",
            "slot_definitions": [
                slot("X Axis", "Category", "column", True, False, "Choose the category or axis column"),
                slot("Y Axis / Value", "Y", "measure", True, False, "Choose the measure to plot"),
                slot("Legend", "Legend", "column", False, False, "Optional legend grouping"),
                slot("Tooltip", "Tooltip", "any", False, False, "Optional tooltip fields"),
            ],
            "default_format": {},
            "is_active": "1",
            "category": "Chart",
            "icon": "show_chart",
            "description": "Show trends over time.",
            "default_width": 4,
            "default_height": 3,
            "required_slots": [
                {"key": "Category", "label": "Category", "kind": "column"},
                {"key": "Y", "label": "Y", "kind": "measure"},
            ],
            "optional_slots": [
                {"key": "Legend", "label": "Legend", "kind": "column"},
                {"key": "Tooltip", "label": "Tooltip", "kind": "any"},
            ],
            "default_visual_json": {"visualType": "lineChart"},
        },
        {
            "template_key": "areaChart",
            "name": "Area Chart",
            "visual_type": "areaChart",
            "slot_definitions": [
                slot("X Axis", "Category", "column", True, False, "Choose the category or axis column"),
                slot("Y Axis / Value", "Y", "measure", True, False, "Choose the measure to plot"),
                slot("Legend", "Legend", "column", False, False, "Optional legend grouping"),
            ],
            "default_format": {},
            "is_active": "1",
            "category": "Chart",
            "icon": "area_chart",
            "description": "Show filled trends over time.",
            "default_width": 4,
            "default_height": 3,
            "required_slots": [
                {"key": "Category", "label": "Category", "kind": "column"},
                {"key": "Y", "label": "Y", "kind": "measure"},
            ],
            "optional_slots": [{"key": "Legend", "label": "Legend", "kind": "column"}],
            "default_visual_json": {"visualType": "areaChart"},
        },
        {
            "template_key": "card",
            "name": "KPI Card",
            "visual_type": "card",
            "slot_definitions": [
                slot("Values", "Values", "measure", True, False, "The KPI value"),
            ],
            "default_format": {},
            "is_active": "1",
            "category": "KPI",
            "icon": "credit_card",
            "description": "Show a single aggregated number.",
            "default_width": 2,
            "default_height": 2,
            "required_slots": [{"key": "Values", "label": "Values", "kind": "measure"}],
            "optional_slots": [],
            "default_visual_json": {"visualType": "card"},
        },
        {
            "template_key": "multiRowCard",
            "name": "Multi-Row Card",
            "visual_type": "multiRowCard",
            "slot_definitions": [
                slot("Values", "Values", "any", True, True, "Displayed values"),
            ],
            "default_format": {},
            "is_active": "1",
            "category": "KPI",
            "icon": "grid_3x3",
            "description": "Show multiple fields in a card layout.",
            "default_width": 3,
            "default_height": 3,
            "required_slots": [{"key": "Values", "label": "Values", "kind": "any"}],
            "optional_slots": [],
            "default_visual_json": {"visualType": "multiRowCard"},
        },
        {
            "template_key": "tableEx",
            "name": "Table",
            "visual_type": "tableEx",
            "slot_definitions": [
                slot("Values", "Values", "any", True, True, "Table columns"),
            ],
            "default_format": {},
            "is_active": "1",
            "category": "Table",
            "icon": "table_chart",
            "description": "Display detailed rows and columns.",
            "default_width": 5,
            "default_height": 4,
            "required_slots": [{"key": "Values", "label": "Values", "kind": "any"}],
            "optional_slots": [],
            "default_visual_json": {"visualType": "tableEx"},
        },
        {
            "template_key": "matrix",
            "name": "Matrix",
            "visual_type": "matrix",
            "slot_definitions": [
                slot("Rows", "Rows", "column", True, True, "Row fields"),
                slot("Columns", "Columns", "column", True, True, "Column fields"),
                slot("Values", "Values", "measure", True, True, "Matrix values"),
            ],
            "default_format": {},
            "is_active": "1",
            "category": "Table",
            "icon": "grid_on",
            "description": "Display a pivot-style summary.",
            "default_width": 5,
            "default_height": 4,
            "required_slots": [
                {"key": "Rows", "label": "Rows", "kind": "column"},
                {"key": "Columns", "label": "Columns", "kind": "column"},
                {"key": "Values", "label": "Values", "kind": "measure"},
            ],
            "optional_slots": [],
            "default_visual_json": {"visualType": "matrix"},
        },
        {
            "template_key": "donutChart",
            "name": "Pie / Donut",
            "visual_type": "donutChart",
            "slot_definitions": [
                slot("Category", "Category", "column", True, False, "Category slice"),
                slot("Y", "Y", "measure", True, False, "Slice value"),
                slot("Tooltip", "Tooltip", "any", False, False, "Optional tooltip"),
            ],
            "default_format": {},
            "is_active": "1",
            "category": "Chart",
            "icon": "pie_chart",
            "description": "Show part-to-whole contribution.",
            "default_width": 3,
            "default_height": 3,
            "required_slots": [
                {"key": "Category", "label": "Category", "kind": "column"},
                {"key": "Y", "label": "Y", "kind": "measure"},
            ],
            "optional_slots": [{"key": "Tooltip", "label": "Tooltip", "kind": "any"}],
            "default_visual_json": {"visualType": "donutChart"},
        },
        {
            "template_key": "slicer",
            "name": "Slicer",
            "visual_type": "slicer",
            "slot_definitions": [
                slot("Field", "Field", "column", True, False, "Filter field"),
            ],
            "default_format": {},
            "is_active": "1",
            "category": "Filter",
            "icon": "filter_alt",
            "description": "Filter the report by a field.",
            "default_width": 2,
            "default_height": 3,
            "required_slots": [{"key": "Field", "label": "Field", "kind": "column"}],
            "optional_slots": [],
            "default_visual_json": {"visualType": "slicer"},
        },
    ]


def seed_visual_templates():
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        loader = DBLoader(conn)
        existing_by_key = {row.get("template_key"): row for row in reader.get_visual_templates()}
        for template in _default_visual_templates():
            existing = existing_by_key.get(template["template_key"])
            if existing:
                loader.update_visual_template(
                    existing["id"],
                    template_key=template["template_key"],
                    name=template["name"],
                    category=template["category"],
                    icon=template["icon"],
                    description=template["description"],
                    default_width=template["default_width"],
                    default_height=template["default_height"],
                    required_slots=template["required_slots"],
                    optional_slots=template["optional_slots"],
                    default_visual_json=template["default_visual_json"],
                    visual_type=template["visual_type"],
                    slot_definitions=template["slot_definitions"],
                    default_format=template["default_format"],
                    is_active=template["is_active"],
                )
                continue

            loader.insert_visual_template(
                template_key=template["template_key"],
                name=template["name"],
                category=template["category"],
                icon=template["icon"],
                description=template["description"],
                default_width=template["default_width"],
                default_height=template["default_height"],
                required_slots=template["required_slots"],
                optional_slots=template["optional_slots"],
                default_visual_json=template["default_visual_json"],
                visual_type=template["visual_type"],
                slot_definitions=template["slot_definitions"],
                default_format=template["default_format"],
                is_active=template["is_active"],
            )


def list_visual_templates():
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        templates = [template for template in reader.get_visual_templates() if str(template.get("is_active", "1")) == "1"]
        if not templates:
            seed_visual_templates()
            templates = [template for template in reader.get_visual_templates() if str(template.get("is_active", "1")) == "1"]
        return [
            {
                **template,
                "slot_definitions": template.get("slot_definitions") or _visual_slot_definitions(template),
            }
            for template in templates
        ]


def import_visual_templates_from_pbip(upload):
    init_db()
    if not upload.filename or not upload.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload must be a .zip archive containing a PBIP report.")

    request_id = uuid.uuid4().hex
    request_root = Path(WORK_ROOT) / "template-imports" / request_id
    upload_path = request_root / "upload.zip"
    extracted_root = request_root / "pbip"
    _ensure_directory(request_root)

    try:
        with open(upload_path, "wb") as fh:
            shutil.copyfileobj(upload.file, fh)
        _unzip_archive(upload_path, extracted_root)
        report_path = _find_report_folder(extracted_root)
        if not report_path:
            raise FileNotFoundError("No '.Report' folder found in uploaded PBIP archive.")

        extracted_report = ReportExtractor(report_path).extract()
        report_name = extracted_report.get("report", {}).get("name") or Path(upload.filename).stem
        source_file = upload.filename
        created = 0
        updated = 0
        skipped = 0
        templates = []

        for page in extracted_report.get("pages", []) or []:
            page_name = page.get("name") or "Page"
            for visual in page.get("visuals", []) or []:
                visual_name = visual.get("name") or "Visual"
                visual_json = visual.get("visual") or {}
                template_payload = _build_template_payload(report_name, page_name, visual_name, visual_json, source_file)
                if not template_payload["slot_definitions"]:
                    template_payload["is_active"] = "0"
                templates.append(template_payload)

        with engine.begin() as conn:
            reader = DBReader(conn)
            loader = DBLoader(conn)
            for template in templates:
                existing = reader.get_visual_template_by_key(template["template_key"])
                if existing:
                    loader.update_visual_template(
                        existing["id"],
                        name=template["name"],
                        category=template["category"],
                        icon=template["icon"],
                        description=template["description"],
                        default_width=template["default_width"],
                        default_height=template["default_height"],
                        required_slots=template["required_slots"],
                        optional_slots=template["optional_slots"],
                        default_visual_json=template["default_visual_json"],
                        visual_type=template["visual_type"],
                        slot_definitions=template["slot_definitions"],
                        default_format=template["default_format"],
                        is_active=template["is_active"],
                    )
                    updated += 1
                    continue

                loader.insert_visual_template(
                    template_key=template["template_key"],
                    name=template["name"],
                    category=template["category"],
                    icon=template["icon"],
                    description=template["description"],
                    default_width=template["default_width"],
                    default_height=template["default_height"],
                    required_slots=template["required_slots"],
                    optional_slots=template["optional_slots"],
                    default_visual_json=template["default_visual_json"],
                    visual_type=template["visual_type"],
                    slot_definitions=template["slot_definitions"],
                    default_format=template["default_format"],
                    is_active=template["is_active"],
                )
                created += 1
        return {
            "message": "PBIP template import complete.",
            "report_name": report_name,
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "template_count": created + updated,
        }
    except Exception:
        raise
    finally:
        _safe_delete_path(request_root)


def _row_to_visual(row):
    return {
        "id": row["id"],
        "canvas_page_id": row["canvas_page_id"],
        "visual_order": row.get("visual_order", 0),
        "template_key": row["template_key"],
        "name": row["name"],
        "x": row.get("x", 0),
        "y": row.get("y", 0),
        "w": row.get("w", 3),
        "h": row.get("h", 2),
        "bindings": row.get("bindings") or {},
        "config": row.get("config") or {},
        "raw": row.get("raw") or {},
    }


def _row_to_page(row, visuals=None):
    return {
        "id": row["id"],
        "canvas_report_id": row["canvas_report_id"],
        "page_order": row.get("page_order", 0),
        "name": row["name"],
        "display_name": row.get("display_name") or row["name"],
        "width": row.get("width") or DEFAULT_CANVAS_WIDTH,
        "height": row.get("height") or DEFAULT_CANVAS_HEIGHT,
        "raw": row.get("raw") or {},
        "visuals": visuals or [],
    }


def get_canvas_report_detail(canvas_report_id):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        report = reader.get_canvas_report(canvas_report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Canvas report {canvas_report_id} not found.")
        pages = []
        for page in reader.get_canvas_pages(canvas_report_id):
            visuals = [_row_to_visual(row) for row in reader.get_canvas_visuals(page["id"])]
            pages.append(_row_to_page(page, visuals=visuals))
    return {
        "id": report["id"],
        "name": report["name"],
        "description": report.get("description"),
        "source_semantic_model_id": report.get("source_semantic_model_id"),
        "source_semantic_model_name": report.get("source_semantic_model_name"),
        "canvas_settings": report.get("canvas_settings") or {},
        "report_settings": report.get("report_settings") or {},
        "raw": report.get("raw") or {},
        "pages": pages,
    }


def list_canvas_reports():
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        reports = reader.get_canvas_reports()
        results = []
        for report in reports:
            page_count = len(reader.get_canvas_pages(report["id"]))
            results.append(
                {
                    "id": report["id"],
                    "name": report["name"],
                    "description": report.get("description"),
                    "source_semantic_model_id": report.get("source_semantic_model_id"),
                    "source_semantic_model_name": report.get("source_semantic_model_name"),
                    "canvas_settings": report.get("canvas_settings") or {},
                    "report_settings": report.get("report_settings") or {},
                    "page_count": page_count,
                }
            )
        return results


def _assert_source_semantic_model_exists(source_semantic_model_id):
    with engine.begin() as conn:
        row = conn.execute(
            select(semantic_models).where(semantic_models.c.id == source_semantic_model_id)
        ).first()
        if not row:
            raise HTTPException(
                status_code=400,
                detail=f"Source semantic model {source_semantic_model_id} was not found.",
            )
        return dict(row._mapping)


def _build_canvas_raw(report_row, pages):
    raw = deepcopy(report_row.get("raw") or {})
    raw["name"] = report_row["name"]
    raw["description"] = report_row.get("description")
    raw["source_semantic_model_id"] = report_row.get("source_semantic_model_id")
    raw["source_semantic_model_name"] = report_row.get("source_semantic_model_name")
    raw["canvas_settings"] = report_row.get("canvas_settings") or {}
    raw["report_settings"] = report_row.get("report_settings") or {}
    raw["pages"] = pages
    return raw


def create_canvas_report(payload):
    init_db()
    source_semantic_model = _assert_source_semantic_model_exists(payload.source_semantic_model_id)
    source_semantic_model_name = payload.source_semantic_model_name or source_semantic_model["name"]
    canvas_settings = payload.canvas_settings or {}
    report_settings = payload.report_settings or {}

    pages = payload.pages or [
        {
            "name": "Page 1",
            "display_name": "Page 1",
            "width": canvas_settings.get("width", DEFAULT_CANVAS_WIDTH),
            "height": canvas_settings.get("height", DEFAULT_CANVAS_HEIGHT),
            "raw": {},
            "page_order": 0,
            "visuals": [],
        }
    ]

    with engine.begin() as conn:
        loader = DBLoader(conn)
        report_id = loader.insert_canvas_report(
            name=payload.name,
            description=payload.description,
            source_semantic_model_id=payload.source_semantic_model_id,
            source_semantic_model_name=source_semantic_model_name,
            canvas_settings=canvas_settings,
            report_settings=report_settings,
            raw={},
        )
        for page_index, page in enumerate(pages):
            page_data = _as_dict(page)
            page_id = loader.insert_canvas_page(
                canvas_report_id=report_id,
                page_order=page_data.get("page_order", page_index),
                name=page_data["name"],
                display_name=page_data.get("display_name") or page_data["name"],
                width=page_data.get("width", canvas_settings.get("width", DEFAULT_CANVAS_WIDTH)),
                height=page_data.get("height", canvas_settings.get("height", DEFAULT_CANVAS_HEIGHT)),
                raw=page_data.get("raw") or {},
            )
            for visual_index, visual in enumerate(page_data.get("visuals") or []):
                visual_data = _as_dict(visual)
                loader.insert_canvas_visual(
                    canvas_page_id=page_id,
                    visual_order=visual_data.get("visual_order", visual_index),
                    template_key=visual_data["template_key"],
                    name=visual_data.get("name") or visual_data["template_key"],
                    x=visual_data.get("x", 0),
                    y=visual_data.get("y", 0),
                    w=visual_data.get("w", 3),
                    h=visual_data.get("h", 2),
                    bindings=visual_data.get("bindings") or {},
                    config=visual_data.get("config") or {},
                    raw=visual_data.get("raw") or {},
                )
        report_row = loader.conn.execute(
            select(canvas_reports).where(canvas_reports.c.id == report_id)
        ).first()
    return get_canvas_report_detail(report_id)


def update_canvas_report(canvas_report_id, payload):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        report = reader.get_canvas_report(canvas_report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Canvas report {canvas_report_id} not found.")
        values = {}
        for key in (
            "name",
            "description",
            "source_semantic_model_id",
            "source_semantic_model_name",
            "canvas_settings",
            "report_settings",
            "raw",
        ):
            value = getattr(payload, key)
            if value is not None:
                values[key] = value
        if "source_semantic_model_id" in values:
            _assert_source_semantic_model_exists(values["source_semantic_model_id"])
        if values:
            conn.execute(
                update(canvas_reports)
                .where(canvas_reports.c.id == canvas_report_id)
                .values(**values)
            )
    return get_canvas_report_detail(canvas_report_id)


def snapshot_canvas_report(canvas_report_id, payload):
    init_db()
    report_update = {
        key: getattr(payload, key)
        for key in (
            "name",
            "description",
            "source_semantic_model_id",
            "source_semantic_model_name",
            "canvas_settings",
            "report_settings",
            "raw",
        )
        if getattr(payload, key) is not None
    }
    if "source_semantic_model_id" in report_update:
        _assert_source_semantic_model_exists(report_update["source_semantic_model_id"])

    with engine.begin() as conn:
        reader = DBReader(conn)
        loader = DBLoader(conn)
        report = reader.get_canvas_report(canvas_report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Canvas report {canvas_report_id} not found.")
        if report_update:
            conn.execute(
                update(canvas_reports)
                .where(canvas_reports.c.id == canvas_report_id)
                .values(**report_update)
            )

        existing_pages = {page["id"]: page for page in reader.get_canvas_pages(canvas_report_id)}
        payload_pages = payload.pages or []
        payload_page_ids = {page.id for page in payload_pages if getattr(page, "id", None)}
        pages_to_delete = [page_id for page_id in existing_pages if page_id not in payload_page_ids]
        if pages_to_delete:
            conn.execute(
                delete(canvas_visuals).where(canvas_visuals.c.canvas_page_id.in_(pages_to_delete))
            )
            conn.execute(
                delete(canvas_pages).where(canvas_pages.c.id.in_(pages_to_delete))
            )

        for page_index, page in enumerate(payload_pages):
            page_data = _as_dict(page)
            page_values = {
                "canvas_report_id": canvas_report_id,
                "page_order": page_index,
                "name": page_data["name"],
                "display_name": page_data.get("display_name") or page_data["name"],
                "width": page_data.get("width", DEFAULT_CANVAS_WIDTH),
                "height": page_data.get("height", DEFAULT_CANVAS_HEIGHT),
                "raw": page_data.get("raw") or {},
            }
            page_id = page_data.get("id")
            if page_id and page_id in existing_pages:
                conn.execute(
                    update(canvas_pages)
                    .where(canvas_pages.c.id == page_id)
                    .values(**page_values)
                )
            else:
                page_id = loader.insert_canvas_page(**page_values)

            existing_visuals = {
                visual["id"]: visual for visual in reader.get_canvas_visuals(page_id)
            }
            payload_visuals = page_data.get("visuals") or []
            payload_visual_ids = {
                _as_dict(visual).get("id") for visual in payload_visuals if _as_dict(visual).get("id")
            }
            visuals_to_delete = [
                visual_id for visual_id in existing_visuals if visual_id not in payload_visual_ids
            ]
            if visuals_to_delete:
                conn.execute(
                    delete(canvas_visuals).where(canvas_visuals.c.id.in_(visuals_to_delete))
                )

            for visual_index, visual in enumerate(payload_visuals):
                visual_data = _as_dict(visual)
                visual_values = {
                    "canvas_page_id": page_id,
                    "visual_order": visual_index,
                    "template_key": visual_data["template_key"],
                    "name": visual_data.get("name") or visual_data["template_key"],
                    "x": visual_data.get("x", 0),
                    "y": visual_data.get("y", 0),
                    "w": visual_data.get("w", 3),
                    "h": visual_data.get("h", 2),
                    "bindings": visual_data.get("bindings") or {},
                    "config": visual_data.get("config") or {},
                    "raw": visual_data.get("raw") or {},
                }
                visual_id = visual_data.get("id")
                if visual_id and visual_id in existing_visuals:
                    conn.execute(
                        update(canvas_visuals)
                        .where(canvas_visuals.c.id == visual_id)
                        .values(**visual_values)
                    )
                else:
                    loader.insert_canvas_visual(**visual_values)
    return get_canvas_report_detail(canvas_report_id)


def delete_canvas_report(canvas_report_id):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        report = reader.get_canvas_report(canvas_report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Canvas report {canvas_report_id} not found.")
        loader = DBLoader(conn)
        loader.delete_canvas_report(canvas_report_id)
    return {"message": f"Canvas report '{report['name']}' deleted successfully.", "id": canvas_report_id}


def create_canvas_page(canvas_report_id, payload):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        loader = DBLoader(conn)
        report = reader.get_canvas_report(canvas_report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Canvas report {canvas_report_id} not found.")
        page_id = loader.insert_canvas_page(
            canvas_report_id=canvas_report_id,
            page_order=payload.page_order,
            name=payload.name,
            display_name=payload.display_name or payload.name,
            width=payload.width,
            height=payload.height,
            raw=payload.raw or {},
        )
    return _page_detail(page_id)


def update_canvas_page(canvas_page_id, payload):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        page = reader.get_canvas_page(canvas_page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Canvas page {canvas_page_id} not found.")
        values = {}
        for key in ("name", "display_name", "width", "height", "raw", "page_order"):
            value = getattr(payload, key)
            if value is not None:
                values[key if key != "page_order" else "page_order"] = value
        if values:
            conn.execute(
                update(canvas_pages)
                .where(canvas_pages.c.id == canvas_page_id)
                .values(**values)
            )
    return _page_detail(canvas_page_id)


def delete_canvas_page(canvas_page_id):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        page = reader.get_canvas_page(canvas_page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Canvas page {canvas_page_id} not found.")
        conn.execute(delete(canvas_visuals).where(canvas_visuals.c.canvas_page_id == canvas_page_id))
        conn.execute(delete(canvas_pages).where(canvas_pages.c.id == canvas_page_id))
    return {"message": f"Canvas page '{page['name']}' deleted successfully.", "id": canvas_page_id}


def create_canvas_visual(canvas_page_id, payload):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        loader = DBLoader(conn)
        page = reader.get_canvas_page(canvas_page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Canvas page {canvas_page_id} not found.")
        visual_id = loader.insert_canvas_visual(
            canvas_page_id=canvas_page_id,
            visual_order=payload.visual_order,
            template_key=payload.template_key,
            name=payload.name or payload.template_key,
            x=payload.x,
            y=payload.y,
            w=payload.w,
            h=payload.h,
            bindings=payload.bindings or {},
            config=payload.config or {},
            raw=payload.raw or {},
        )
    return _visual_detail(visual_id)


def update_canvas_visual(canvas_visual_id, payload):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        visual = reader.get_canvas_visual(canvas_visual_id)
        if not visual:
            raise HTTPException(status_code=404, detail=f"Canvas visual {canvas_visual_id} not found.")
        values = {}
        for key in ("template_key", "name", "x", "y", "w", "h", "bindings", "config", "raw", "visual_order"):
            value = getattr(payload, key)
            if value is not None:
                values["visual_order" if key == "visual_order" else key] = value
        if values:
            conn.execute(
                update(canvas_visuals)
                .where(canvas_visuals.c.id == canvas_visual_id)
                .values(**values)
            )
    return _visual_detail(canvas_visual_id)


def delete_canvas_visual(canvas_visual_id):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        visual = reader.get_canvas_visual(canvas_visual_id)
        if not visual:
            raise HTTPException(status_code=404, detail=f"Canvas visual {canvas_visual_id} not found.")
        conn.execute(delete(canvas_visuals).where(canvas_visuals.c.id == canvas_visual_id))
    return {"message": f"Canvas visual '{visual['name']}' deleted successfully.", "id": canvas_visual_id}


def _page_detail(page_id):
    with engine.begin() as conn:
        reader = DBReader(conn)
        page = reader.get_canvas_page(page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Canvas page {page_id} not found.")
        visuals = [_row_to_visual(row) for row in reader.get_canvas_visuals(page_id)]
        return _row_to_page(page, visuals=visuals)


def _visual_detail(visual_id):
    with engine.begin() as conn:
        reader = DBReader(conn)
        visual = reader.get_canvas_visual(visual_id)
        if not visual:
            raise HTTPException(status_code=404, detail=f"Canvas visual {visual_id} not found.")
        return _row_to_visual(visual)


def _parse_field_options(dataset_raw):
    tables = []
    fields = []
    relationships = []
    model = dataset_raw.get("model") or {}

    def append_field(table_name, entry):
        entry.setdefault("table", table_name)
        entry.setdefault("label", f"{table_name}[{entry.get('name') or 'Field'}]")
        fields.append(entry)
        table_map.setdefault(table_name, []).append(entry)

    table_map = {}

    for table in model.get("tables", []) or []:
        table_name = table.get("name") or "Table"
        table_fields = []

        for column in table.get("columns", []) or []:
            field = {
                "table": table_name,
                "name": column.get("name") or "Column",
                "kind": "column",
                "data_type": column.get("dataType") or column.get("type"),
                "label": f"{table_name}[{column.get('name') or 'Column'}]",
            }
            append_field(table_name, field)
            table_fields.append(field)

        for measure in table.get("measures", []) or []:
            field = {
                "table": table_name,
                "name": measure.get("name") or "Measure",
                "kind": "measure",
                "data_type": measure.get("dataType") or measure.get("type"),
                "label": f"{table_name}[{measure.get('name') or 'Measure'}]",
            }
            append_field(table_name, field)
            table_fields.append(field)

        tables.append({"table": table_name, "fields": table_fields})

    definition_files = dataset_raw.get("definitionFiles")
    if isinstance(definition_files, dict):
        current_table = None
        current_field = None
        current_kind = None

        def flush_current_field():
            nonlocal current_field, current_kind, current_table
            if current_table and current_field:
                kind = current_kind or "column"
                field = {
                    "table": current_table,
                    "name": current_field.get("name") or "Field",
                    "kind": kind,
                    "data_type": current_field.get("dataType") or current_field.get("type"),
                    "label": f"{current_table}[{current_field.get('name') or 'Field'}]",
                }
                append_field(current_table, field)
            current_field = None
            current_kind = None

        for path_key in sorted(definition_files):
            content = definition_files[path_key]
            if not isinstance(content, str):
                continue

            if path_key.startswith("tables/") and path_key.endswith(".tmdl"):
                current_table = None
                current_field = None
                current_kind = None
                table_name = None

                for raw_line in content.splitlines():
                    stripped = raw_line.strip()
                    if not stripped:
                        continue
                    if not raw_line.startswith("\t") and stripped.startswith("table "):
                        table_name = stripped.split(" ", 1)[1].strip()
                        if not any(item["table"] == table_name for item in tables):
                            tables.append({"table": table_name, "fields": []})
                        current_table = table_name
                        continue

                    if current_table is None:
                        continue

                    if not raw_line.startswith("\t\t") and stripped.startswith("column "):
                        flush_current_field()
                        current_kind = "column"
                        current_field = {"name": stripped.split(" ", 1)[1].strip()}
                        continue

                    if not raw_line.startswith("\t\t") and stripped.startswith("measure "):
                        flush_current_field()
                        current_kind = "measure"
                        current_field = {"name": stripped.split(" ", 1)[1].strip()}
                        continue

                    if current_field is None:
                        continue

                    if ":" in stripped:
                        key, value = stripped.split(":", 1)
                        current_field[key.strip()] = value.strip().strip('"')

                flush_current_field()

            elif path_key.endswith("relationships.tmdl"):
                current_relationship = None
                for raw_line in content.splitlines():
                    stripped = raw_line.strip()
                    if not stripped:
                        continue
                    if not raw_line.startswith("\t") and stripped.startswith("relationship "):
                        if current_relationship:
                            relationships.append(current_relationship)
                        current_relationship = {"name": stripped.split(" ", 1)[1].strip()}
                        continue
                    if current_relationship and ":" in stripped:
                        key, value = stripped.split(":", 1)
                        current_relationship[key.strip()] = value.strip().strip('"')
                if current_relationship:
                    relationships.append(current_relationship)

    if not tables:
        for table_name, table_fields in table_map.items():
            tables.append({"table": table_name, "fields": table_fields})

    return tables, fields, relationships


def get_semantic_fields(source_project_id):
    init_db()
    source_semantic_model = _assert_source_semantic_model_exists(source_project_id)
    with engine.begin() as conn:
        reader = DBReader(conn)
        semantic_model = reader.get_semantic_model(source_project_id)
        if not semantic_model:
            raise HTTPException(
                status_code=404,
                detail=f"Semantic model for source model {source_project_id} was not found.",
            )
    tables, fields, relationships = _parse_field_options(semantic_model.get("raw") or {})
    return {
        "source_semantic_model_id": source_project_id,
        "source_semantic_model_name": source_semantic_model["name"],
        "tables": tables,
        "fields": fields,
        "relationships": relationships,
    }


def _binding_to_projection(field_binding):
    if isinstance(field_binding, str):
        return {
            "field": field_binding,
            "kind": "field",
        }
    if not isinstance(field_binding, dict):
        return {}
    label = field_binding.get("label")
    if not label and field_binding.get("table") and field_binding.get("name"):
        label = f"{field_binding['table']}[{field_binding['name']}]"
    return {
        "table": field_binding.get("table"),
        "field": field_binding.get("name"),
        "kind": field_binding.get("kind") or "field",
        "label": label,
        "dataType": field_binding.get("data_type"),
    }


def _visual_type_for_template(template, payload):
    default_json = template.get("default_visual_json") or {}
    return payload.get("template_key") and default_json.get("visualType") or default_json.get("visualType") or payload.get("template_key")


def _build_visual_json(visual_row, template, canvas_settings):
    width = canvas_settings.get("width", DEFAULT_CANVAS_WIDTH)
    height = canvas_settings.get("height", DEFAULT_CANVAS_HEIGHT)
    px_per_col = width / DEFAULT_GRID_COLUMNS
    px_per_row = DEFAULT_ROW_HEIGHT
    visual_bindings = visual_row.get("bindings") or {}
    projections = {}
    for slot_key, binding in visual_bindings.items():
        if isinstance(binding, list):
            projections[slot_key] = [_binding_to_projection(item) for item in binding]
        else:
            projections[slot_key] = [_binding_to_projection(binding)]

    return {
        "visualType": _visual_type_for_template(template, visual_row),
        "name": visual_row.get("name") or template["name"],
        "position": {
            "x": int(visual_row.get("x", 0) * px_per_col),
            "y": int(visual_row.get("y", 0) * px_per_row),
            "width": int(visual_row.get("w", 3) * px_per_col),
            "height": int(visual_row.get("h", 2) * px_per_row),
        },
        "query": {
            "queryState": {
                "projections": projections,
            }
        },
        "config": deepcopy(visual_row.get("config") or {}),
        "bindings": deepcopy(visual_bindings),
        "templateKey": visual_row.get("template_key"),
    }


def _build_page_payload(page_row, visual_rows, template_map, canvas_settings, report_settings):
    page_width = page_row.get("width") or canvas_settings.get("width", DEFAULT_CANVAS_WIDTH)
    page_height = page_row.get("height") or canvas_settings.get("height", DEFAULT_CANVAS_HEIGHT)
    page_name = page_row.get("display_name") or page_row.get("name")
    page_json = _default_page_page_json(page_name, page_width, page_height)
    page_json["displayName"] = page_name

    visuals = []
    for visual_row in visual_rows:
        template = template_map.get(visual_row["template_key"]) or {
            "name": visual_row["template_key"],
            "default_visual_json": {"visualType": visual_row["template_key"]},
        }
        visuals.append(
            {
                "name": visual_row.get("name") or visual_row["template_key"],
                "visual": _build_visual_json(visual_row, template, canvas_settings),
            }
        )
    return {
        "name": page_row.get("name"),
        "page": page_json,
        "visuals": visuals,
    }


def _dataset_reference_for_source(source_semantic_model):
    semantic_folder = source_semantic_model.get("semantic_model_folder_name") or f"{source_semantic_model['name']}.SemanticModel"
    return {
        "byPath": {
            "path": f"../{semantic_folder}",
        }
    }


def _prepare_semantic_model_output(output_root, source_semantic_model):
    semantic_folder_name = source_semantic_model.get("semantic_model_folder_name") or f"{source_semantic_model['name']}.SemanticModel"
    semantic_target = Path(output_root) / semantic_folder_name
    _ensure_directory(semantic_target.parent)

    with engine.begin() as conn:
        reader = DBReader(conn)
        source_files = reader.get_semantic_model_files_by_scope(source_semantic_model["id"], "semantic_model")
        dataset = reader.get_semantic_model(source_semantic_model["id"])

    if source_files:
        _write_project_files(semantic_target, source_files)
        return semantic_folder_name

    if not dataset:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to locate a semantic model for '{source_semantic_model['name']}'.",
        )

    SemanticModelWriter(output_root).write(dataset.get("raw") or {}, project_name=source_semantic_model["name"])
    return semantic_folder_name


def compile_canvas_report(canvas_report_id):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        report = reader.get_canvas_report(canvas_report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Canvas report {canvas_report_id} not found.")
        source_semantic_model = conn.execute(
            select(semantic_models).where(semantic_models.c.id == report["source_semantic_model_id"])
        ).first()
        if not source_semantic_model:
            raise HTTPException(
                status_code=400,
                detail=f"Source semantic model {report['source_semantic_model_id']} for canvas report {canvas_report_id} was not found.",
            )
        source_semantic_model = dict(source_semantic_model._mapping)
        pages = reader.get_canvas_pages(canvas_report_id)
        template_rows = reader.get_visual_templates()
        template_map = {row["template_key"]: row for row in template_rows}

        canvas_settings = report.get("canvas_settings") or {}
        report_settings = report.get("report_settings") or {}
        payload_pages = []
        for page in pages:
            visuals = reader.get_canvas_visuals(page["id"])
            payload_pages.append(
                _build_page_payload(page, visuals, template_map, canvas_settings, report_settings)
            )

        compile_id = uuid.uuid4().hex
        compile_root = Path(WORK_ROOT) / "compiles" / compile_id
        _ensure_directory(compile_root)

        semantic_folder_name = _prepare_semantic_model_output(compile_root, source_semantic_model)
        report_folder_name = f"{_safe_name(report['name'], fallback='Draft')}.Report"
        report_payload = {
            "projectName": report["name"],
            "reportFolderName": report_folder_name,
            "semanticModelFolderName": semantic_folder_name,
            "definitionPbir": {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
                "version": "4.0",
                "datasetReference": _dataset_reference_for_source(source_semantic_model),
            },
            "report": _default_report_json(report_settings, canvas_settings),
            "pages": payload_pages,
        }

        ReportWriter(str(compile_root)).write(
            report_payload,
            project_name=report["name"],
            dataset_reference=_dataset_reference_for_source(source_semantic_model),
        )

        safe_report_name = _safe_name(report["name"], fallback="Draft")
        pbip_path = compile_root / f"{safe_report_name}.pbip"
        _safe_write_json(
            pbip_path,
            {
                "$schema": PBIP_SCHEMA_URL,
                "version": "1.0",
                "artifacts": [{"report": {"path": report_folder_name}}],
                "settings": {"enableAutoRecovery": True},
            },
        )

        archive_name = f"{safe_report_name}.zip"
        archive_path = compile_root.parent / f"{safe_report_name}-{compile_id}.zip"
        _create_zip_archive(compile_root, archive_path)

    return archive_path, archive_name, compile_root


def cleanup_compile_output(output_root, archive_path=None):
    _safe_delete_path(output_root)
    if archive_path:
        _safe_delete_path(archive_path)


def _sanitize_page_name(page_name):
    page_name = re.sub(r"[^A-Za-z0-9_]+", "_", (page_name or "").strip())
    page_name = page_name.strip("_")
    return page_name or "page_1"


def _visual_template_type(template):
    return (
        template.get("visual_type")
        or template.get("visualType")
        or (template.get("default_visual_json") or {}).get("visualType")
        or template.get("template_key")
    )


def _visual_slot_definitions(template):
    slots = template.get("slot_definitions")
    if isinstance(slots, list) and slots:
        return slots

    derived = []
    for slot in template.get("required_slots") or []:
        derived.append(
            {
                "name": slot.get("label") or slot.get("key") or slot.get("name"),
                "role": slot.get("key") or slot.get("name"),
                "field_type": "measure" if "measure" in str(slot.get("kind")) else "column",
                "required": True,
                "multi": "list" in str(slot.get("kind") or ""),
                "description": slot.get("description") or "",
            }
        )
    for slot in template.get("optional_slots") or []:
        derived.append(
            {
                "name": slot.get("label") or slot.get("key") or slot.get("name"),
                "role": slot.get("key") or slot.get("name"),
                "field_type": "measure" if "measure" in str(slot.get("kind")) else "any",
                "required": False,
                "multi": "list" in str(slot.get("kind") or ""),
                "description": slot.get("description") or "",
            }
        )
    return derived


def _canvas_report_settings(report_row):
    settings = report_row.get("settings") or {}
    canvas_settings = report_row.get("canvas_settings") or {}
    report_settings = report_row.get("report_settings") or {}
    return {
        "theme_color": settings.get("theme_color") or report_settings.get("themeColor") or "#154360",
        "canvas_width": settings.get("canvas_width") or canvas_settings.get("width") or DEFAULT_CANVAS_WIDTH,
        "canvas_height": settings.get("canvas_height") or canvas_settings.get("height") or DEFAULT_CANVAS_HEIGHT,
    }


def _default_report_json_from_settings(settings):
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.2.0/schema.json",
        "themeCollection": {
            "baseTheme": {
                "name": "BIFoundryTheme",
                "reportVersionAtImport": {
                    "visual": "2.8.0",
                    "report": "3.2.0",
                    "page": "2.3.1",
                },
                "type": "SharedResources",
                "color": settings.get("theme_color") or "#154360",
            }
        },
        "objects": {
            "section": [
                {
                    "properties": {
                        "verticalAlignment": {
                            "expr": {
                                "Literal": {
                                    "Value": "'Top'"
                                }
                            }
                        }
                    }
                }
            ]
        },
        "resourcePackages": [
            {
                "name": "SharedResources",
                "type": "SharedResources",
                "items": [
                    {
                        "name": "BIFoundryTheme",
                        "path": "BaseThemes/BIFoundryTheme.json",
                        "type": "BaseTheme",
                    }
                ],
            }
        ],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
            "useDefaultAggregateDisplayName": True,
            "canvas": {
                "width": settings.get("canvas_width") or DEFAULT_CANVAS_WIDTH,
                "height": settings.get("canvas_height") or DEFAULT_CANVAS_HEIGHT,
            },
        },
    }


def _default_page_json(page_name, display_name, settings):
    width = settings.get("width") or DEFAULT_CANVAS_WIDTH
    height = settings.get("height") or DEFAULT_CANVAS_HEIGHT
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
        "name": page_name,
        "displayName": display_name or page_name,
        "displayOption": settings.get("display_option") or "FitToPage",
        "width": width,
        "height": height,
        "objects": {
            "outspacePane": [
                {
                    "properties": {
                        "width": {
                            "expr": {
                                "Literal": {
                                    "Value": "192L"
                                }
                            }
                        }
                    }
                }
            ]
        },
    }


def _binding_projection(binding):
    if not isinstance(binding, dict):
        return None
    table = binding.get("table")
    field = binding.get("field")
    field_type = binding.get("field_type")
    if not table or not field:
        return None
    if field_type == "measure":
        projection_key = "Measure"
    else:
        projection_key = "Column"
    return {
        "field": {
            projection_key: {
                "Expression": {"SourceRef": {"Entity": table}},
                "Property": field,
            }
        },
        "queryRef": f"{table}.{field}",
        "active": True,
    }


def _visual_json_from_row(visual_row, template, canvas_settings):
    grid_position = visual_row.get("grid_position") or {}
    canvas_width = canvas_settings.get("canvas_width") or DEFAULT_CANVAS_WIDTH
    cell_width = canvas_width / DEFAULT_GRID_COLUMNS
    cell_height = 90.0
    x = float(grid_position.get("col", 0)) * cell_width
    y = float(grid_position.get("row", 0)) * cell_height
    width = float(grid_position.get("w", 3)) * cell_width
    height = float(grid_position.get("h", 2)) * cell_height
    tab_order = float(visual_row.get("tab_order") or 1000)
    field_bindings = visual_row.get("field_bindings") or {}
    projections = {}
    for slot in _visual_slot_definitions(template):
        role = slot.get("role")
        binding = field_bindings.get(role)
        if binding is None:
            continue
        if isinstance(binding, list):
            items = [_binding_projection(item) for item in binding if _binding_projection(item)]
        else:
            projection = _binding_projection(binding)
            items = [projection] if projection else []
        if items:
            projections[role] = items

    return {
        "name": visual_row.get("visual_name") or visual_row.get("name") or uuid.uuid4().hex,
        "position": {
            "x": float(x),
            "y": float(y),
            "z": float(tab_order),
            "tabOrder": float(tab_order),
            "height": float(height),
            "width": float(width),
        },
        "visual": {
            "visualType": _visual_template_type(template),
            "query": {
                "queryState": {
                    "projections": projections,
                }
            },
            "drillFilterOtherVisuals": True,
        },
    }


def _dataset_reference_from_semantic_model(semantic_model_row):
    folder_name = semantic_model_row.get("semantic_model_folder_name") or f"{semantic_model_row['name']}.SemanticModel"
    return {"byPath": {"path": f"../{folder_name}"}}


def _load_semantic_fields(dataset_id):
    with engine.begin() as conn:
        reader = DBReader(conn)
        loader = DBLoader(conn)
        cached_fields = reader.get_dataset_fields(dataset_id)
        if cached_fields:
            return cached_fields

        semantic_model = reader.get_semantic_model(dataset_id)
        if not semantic_model:
            raise HTTPException(status_code=404, detail=f"Semantic model {dataset_id} was not found.")

        tables, fields, _relationships = _parse_field_options(semantic_model.get("raw") or {})
        loader.delete_dataset_fields(dataset_id)
        for field in fields:
            loader.insert_dataset_field(
                dataset_id=dataset_id,
                table_name=field.get("table"),
                field_name=field.get("name"),
                field_type=field.get("kind"),
                data_type=field.get("data_type"),
                dax_expression=field.get("dax_expression"),
            )
        return reader.get_dataset_fields(dataset_id)


def get_canvas_fields_v2(report_id):
    detail = _report_detail_v2(report_id)
    with engine.begin() as conn:
        reader = DBReader(conn)
        semantic_model = reader.get_semantic_model(detail["project_id"])
        if not semantic_model:
            raise HTTPException(status_code=404, detail=f"Semantic model {detail['project_id']} was not found.")
    _load_semantic_fields(detail["project_id"])
    tables, fields, relationships = _parse_field_options(semantic_model.get("raw") or {})
    return {
        "source_semantic_model_id": detail["project_id"],
        "source_semantic_model_name": semantic_model["name"],
        "tables": tables,
        "fields": fields,
        "relationships": relationships,
    }


def list_visual_templates_v2():
    return list_visual_templates()


def list_canvas_reports_v2():
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        reports = []
        for report in reader.get_canvas_reports():
            page_count = len(reader.get_canvas_pages(report["id"]))
            source_name = report.get("source_semantic_model_name")
            if not source_name and report.get("project_id"):
                source_model = reader.get_semantic_model(report["project_id"])
                source_name = source_model["name"] if source_model else None
            reports.append(
                {
                    "id": report["id"],
                    "name": report["name"],
                    "project_id": report.get("project_id"),
                    "source_semantic_model_name": source_name,
                    "settings": report.get("settings") or {},
                    "created_at": report.get("created_at"),
                    "page_count": page_count,
                }
            )
        return reports


def _report_detail_v2(report_id):
    with engine.begin() as conn:
        reader = DBReader(conn)
        report = reader.get_canvas_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Canvas report {report_id} not found.")
        pages = []
        templates = {row["id"]: row for row in reader.get_visual_templates()}
        for page in reader.get_canvas_pages(report_id):
            visuals = []
            for visual in reader.get_canvas_visuals(page["id"]):
                template = templates.get(visual.get("visual_template_id"))
                visuals.append(
                    {
                        "id": visual["id"],
                        "canvas_page_id": visual["canvas_page_id"],
                        "visual_template_id": visual.get("visual_template_id"),
                        "visual_name": visual.get("visual_name") or visual.get("name"),
                        "grid_position": visual.get("grid_position") or {},
                        "field_bindings": visual.get("field_bindings") or {},
                        "format_config": visual.get("format_config") or {},
                        "tab_order": visual.get("tab_order") or visual.get("visual_order") or 1000,
                        "template": template,
                    }
                )
            pages.append(
                {
                    "id": page["id"],
                    "canvas_report_id": page["canvas_report_id"],
                    "page_name": page.get("page_name") or page.get("name"),
                    "display_name": page.get("display_name") or page.get("page_name") or page.get("name"),
                    "page_order": page.get("page_order", 0),
                    "settings": page.get("settings") or {},
                    "visuals": visuals,
                }
            )
        return {
            "id": report["id"],
            "name": report["name"],
            "project_id": report.get("project_id"),
            "settings": report.get("settings") or {},
            "created_at": report.get("created_at"),
            "pages": pages,
        }


def create_canvas_report_v2(payload):
    init_db()
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Report name is required.")
    project_id = payload.get("project_id") or payload.get("dataset_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required.")

    with engine.begin() as conn:
        reader = DBReader(conn)
        loader = DBLoader(conn)
        project = reader.get_semantic_model(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Semantic model {project_id} was not found.")
        settings = payload.get("settings") or {}
        canvas_settings = {
            "width": settings.get("canvas_width", DEFAULT_CANVAS_WIDTH),
            "height": settings.get("canvas_height", DEFAULT_CANVAS_HEIGHT),
        }
        report_settings = {
            "themeColor": settings.get("theme_color"),
        }
        report_id = loader.insert_canvas_report(
            name=name,
            description=payload.get("description"),
            source_semantic_model_id=project_id,
            source_semantic_model_name=project["name"],
            canvas_settings=canvas_settings,
            report_settings=report_settings,
            raw=payload,
            project_id=project_id,
            settings=settings,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        pages = payload.get("pages") or []
        for index, page in enumerate(pages):
            page_name = _sanitize_page_name(page.get("page_name") or page.get("name") or f"page_{index + 1}")
            page_id = loader.insert_canvas_page_v2(
                canvas_report_id=report_id,
                page_name=page_name,
                display_name=page.get("display_name") or page_name,
                page_order=page.get("page_order", index),
                settings=page.get("settings") or {"width": canvas_settings["width"], "height": canvas_settings["height"], "display_option": "FitToPage"},
            )
            for visual_index, visual in enumerate(page.get("visuals") or []):
                loader.insert_canvas_visual_v2(
                    canvas_page_id=page_id,
                    visual_template_id=visual.get("visual_template_id"),
                    visual_name=visual.get("visual_name") or uuid.uuid4().hex,
                    grid_position=visual.get("grid_position") or {"col": 0, "row": 0, "w": 3, "h": 2},
                    field_bindings=visual.get("field_bindings") or {},
                    format_config=visual.get("format_config") or {},
                    tab_order=visual.get("tab_order", 1000 + visual_index),
                )
    return _report_detail_v2(report_id)


def update_canvas_report_v2(report_id, payload):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        report = reader.get_canvas_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Canvas report {report_id} not found.")
        loader = DBLoader(conn)
        name = payload.get("name")
        settings = payload.get("settings")
        loader.update_canvas_report(report_id, name=name, settings=settings)
    return _report_detail_v2(report_id)


def delete_canvas_report_v2(report_id):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        report = reader.get_canvas_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Canvas report {report_id} not found.")
        loader = DBLoader(conn)
        loader.delete_canvas_report(report_id)
    return {"message": f"Canvas report '{report['name']}' deleted successfully.", "id": report_id}


def create_canvas_page_v2(report_id, payload):
    init_db()
    page_name = _sanitize_page_name(payload.get("page_name") or payload.get("name"))
    with engine.begin() as conn:
        reader = DBReader(conn)
        loader = DBLoader(conn)
        report = reader.get_canvas_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Canvas report {report_id} not found.")
        page_id = loader.insert_canvas_page_v2(
            canvas_report_id=report_id,
            page_name=page_name,
            display_name=payload.get("display_name") or page_name,
            page_order=payload.get("page_order", 0),
            settings=payload.get("settings") or {
                "width": (payload.get("settings") or {}).get("width", DEFAULT_CANVAS_WIDTH),
                "height": (payload.get("settings") or {}).get("height", DEFAULT_CANVAS_HEIGHT),
                "display_option": (payload.get("settings") or {}).get("display_option", "FitToPage"),
            },
        )
    return _page_detail_v2(page_id)


def update_canvas_page_v2(page_id, payload):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        page = reader.get_canvas_page(page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Canvas page {page_id} not found.")
        loader = DBLoader(conn)
        page_name = payload.get("page_name")
        if page_name is not None:
            page_name = _sanitize_page_name(page_name)
            loader.conn.execute(
                update(canvas_pages).where(canvas_pages.c.id == page_id).values(
                    page_name=page_name,
                    name=page_name,
                )
            )
        loader.update_canvas_page(
            page_id,
            display_name=payload.get("display_name"),
            page_order=payload.get("page_order"),
            settings=payload.get("settings"),
            page_name=page_name if page_name is not None else None,
        )
    return _page_detail_v2(page_id)


def delete_canvas_page_v2(page_id):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        page = reader.get_canvas_page(page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Canvas page {page_id} not found.")
        loader = DBLoader(conn)
        loader.delete_canvas_page(page_id)
    return {"message": f"Canvas page '{page['name']}' deleted successfully.", "id": page_id}


def create_canvas_visual_v2(report_id, page_id, payload):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        page = reader.get_canvas_page(page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Canvas page {page_id} not found.")
        template_id = payload.get("visual_template_id")
        template = reader.get_visual_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Visual template {template_id} was not found.")
        loader = DBLoader(conn)
        visual_id = loader.insert_canvas_visual_v2(
            canvas_page_id=page_id,
            visual_template_id=template_id,
            visual_name=(payload.get("visual_name") or uuid.uuid4().hex).replace("-", ""),
            grid_position=payload.get("grid_position") or {"col": 0, "row": 0, "w": 3, "h": 2},
            field_bindings=payload.get("field_bindings") or {},
            format_config=payload.get("format_config") or {},
            tab_order=payload.get("tab_order", 1000),
        )
    return _visual_detail_v2(visual_id)


def update_canvas_visual_v2(visual_id, payload):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        visual = reader.get_canvas_visual(visual_id)
        if not visual:
            raise HTTPException(status_code=404, detail=f"Canvas visual {visual_id} not found.")
        loader = DBLoader(conn)
        loader.update_canvas_visual(
            visual_id,
            grid_position=payload.get("grid_position"),
            field_bindings=payload.get("field_bindings"),
            format_config=payload.get("format_config"),
            tab_order=payload.get("tab_order"),
            visual_name=payload.get("visual_name"),
            name=payload.get("name"),
        )
    return _visual_detail_v2(visual_id)


def delete_canvas_visual_v2(visual_id):
    init_db()
    with engine.begin() as conn:
        reader = DBReader(conn)
        visual = reader.get_canvas_visual(visual_id)
        if not visual:
            raise HTTPException(status_code=404, detail=f"Canvas visual {visual_id} not found.")
        loader = DBLoader(conn)
        loader.delete_canvas_visual(visual_id)
    return {"message": f"Canvas visual '{visual['name']}' deleted successfully.", "id": visual_id}


def _page_detail_v2(page_id):
    with engine.begin() as conn:
        reader = DBReader(conn)
        page = reader.get_canvas_page(page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Canvas page {page_id} not found.")
        visuals = []
        templates = {row["id"]: row for row in reader.get_visual_templates()}
        for visual in reader.get_canvas_visuals(page_id):
            template = templates.get(visual.get("visual_template_id"))
            visuals.append(
                {
                    "id": visual["id"],
                    "canvas_page_id": visual["canvas_page_id"],
                    "visual_template_id": visual.get("visual_template_id"),
                    "visual_name": visual.get("visual_name") or visual.get("name"),
                    "grid_position": visual.get("grid_position") or {},
                    "field_bindings": visual.get("field_bindings") or {},
                    "format_config": visual.get("format_config") or {},
                    "tab_order": visual.get("tab_order") or visual.get("visual_order") or 1000,
                    "template": template,
                }
            )
        return {
            "id": page["id"],
            "canvas_report_id": page["canvas_report_id"],
            "page_name": page.get("page_name") or page.get("name"),
            "display_name": page.get("display_name") or page.get("page_name") or page.get("name"),
            "page_order": page.get("page_order", 0),
            "settings": page.get("settings") or {},
            "visuals": visuals,
        }


def _visual_detail_v2(visual_id):
    with engine.begin() as conn:
        reader = DBReader(conn)
        visual = reader.get_canvas_visual(visual_id)
        if not visual:
            raise HTTPException(status_code=404, detail=f"Canvas visual {visual_id} not found.")
        template = reader.get_visual_template(visual.get("visual_template_id"))
        return {
            "id": visual["id"],
            "canvas_page_id": visual["canvas_page_id"],
            "visual_template_id": visual.get("visual_template_id"),
            "visual_name": visual.get("visual_name") or visual.get("name"),
            "grid_position": visual.get("grid_position") or {},
            "field_bindings": visual.get("field_bindings") or {},
            "format_config": visual.get("format_config") or {},
            "tab_order": visual.get("tab_order") or visual.get("visual_order") or 1000,
            "template": template,
        }


def _validate_visual_bindings(visual, template, field_index):
    errors = []
    bindings = visual.get("field_bindings") or {}
    slot_definitions = _visual_slot_definitions(template)
    for slot in slot_definitions:
        role = slot.get("role")
        required = bool(slot.get("required"))
        field_type = slot.get("field_type") or "any"
        binding = bindings.get(role)
        if not binding:
            if required:
                errors.append(
                    {
                        "visual_name": visual.get("visual_name"),
                        "slot": role,
                        "message": f"Required slot '{role}' is unbound.",
                    }
                )
            continue
        if isinstance(binding, list):
            candidates = binding
        else:
            candidates = [binding]
        for candidate in candidates:
            actual_type = candidate.get("field_type")
            if actual_type not in {"column", "measure"}:
                errors.append(
                    {
                        "visual_name": visual.get("visual_name"),
                        "slot": role,
                        "message": f"Slot '{role}' must use field_type 'column' or 'measure'.",
                    }
                )
                continue
            if field_type != "any" and actual_type != field_type:
                errors.append(
                    {
                        "visual_name": visual.get("visual_name"),
                        "slot": role,
                        "message": f"Slot '{role}' expects field_type '{field_type}' but received '{actual_type}'.",
                    }
                )
            if candidate.get("table") and candidate.get("field"):
                key = (candidate["table"], candidate["field"], actual_type)
                if key not in field_index:
                    errors.append(
                        {
                            "visual_name": visual.get("visual_name"),
                            "slot": role,
                            "message": f"Bound field '{candidate['table']}.{candidate['field']}' was not found in dataset fields.",
                        }
                    )
    return errors


def validate_canvas_report_v2(report_id):
    detail = _report_detail_v2(report_id)
    with engine.begin() as conn:
        reader = DBReader(conn)
        templates = {row["id"]: row for row in reader.get_visual_templates()}
        fields = _load_semantic_fields(detail["project_id"])
    field_index = {(field["table_name"], field["field_name"], field["field_type"]) for field in fields}
    errors = []
    for page in detail["pages"]:
        page_name = page.get("page_name")
        sanitized = _sanitize_page_name(page_name)
        if page_name != sanitized:
            errors.append(
                {
                    "page_name": page_name,
                    "message": "page_name must contain only alphanumeric characters and underscores.",
                }
            )
        for visual in page["visuals"]:
            template = templates.get(visual.get("visual_template_id"))
            if not template:
                errors.append(
                    {
                        "visual_name": visual.get("visual_name"),
                        "message": "Visual template not found.",
                    }
                )
                continue
            errors.extend(_validate_visual_bindings(visual, template, field_index))
    return {"valid": not errors, "errors": errors}


def _semantic_model_output_root(report_row):
    project_id = report_row.get("project_id") or report_row.get("source_semantic_model_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="Canvas report is missing a source semantic model.")
    with engine.begin() as conn:
        reader = DBReader(conn)
        semantic_model = reader.get_semantic_model(project_id)
        if not semantic_model:
            raise HTTPException(status_code=404, detail=f"Semantic model {project_id} was not found.")
        return semantic_model


def _page_compile_payload(page_row, visuals, template_map, canvas_settings):
    page_name = _sanitize_page_name(page_row.get("page_name") or page_row.get("display_name") or page_row.get("name"))
    page_settings = page_row.get("settings") or {}
    page_json = _default_page_json(page_name, page_row.get("display_name") or page_name, page_settings or canvas_settings)
    page_payload = {
        "name": page_name,
        "raw": page_json,
        "visuals": [],
    }
    for visual in visuals:
        template = template_map.get(visual.get("visual_template_id")) or {
            "template_key": "unknown",
            "visual_type": "unknown",
            "slot_definitions": [],
            "required_slots": [],
            "optional_slots": [],
            "default_visual_json": {"visualType": "unknown"},
        }
        page_payload["visuals"].append(
            {
                "name": visual.get("visual_name") or uuid.uuid4().hex,
                "raw": _visual_json_from_row(visual, template, canvas_settings),
            }
        )
    return page_payload


def compile_canvas_report_v2(report_id):
    validation = validate_canvas_report_v2(report_id)
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail=validation["errors"])

    init_db()
    request_id = uuid.uuid4().hex
    compile_root = Path(WORK_ROOT) / "canvas_exports" / request_id
    _ensure_directory(compile_root)
    archive_path = None
    try:
        detail = _report_detail_v2(report_id)
        semantic_model = _semantic_model_output_root(detail)
        semantic_folder_name = semantic_model.get("semantic_model_folder_name") or f"{semantic_model['name']}.SemanticModel"
        report_folder_name = f"{_safe_name(detail['name'], fallback='Draft')}.Report"
        dataset_reference = _dataset_reference_from_semantic_model(semantic_model)
        canvas_settings = _canvas_report_settings(detail)
        template_map = {}
        with engine.begin() as conn:
            reader = DBReader(conn)
            template_map = {row["id"]: row for row in reader.get_visual_templates()}
            source_files = reader.get_semantic_model_files_by_scope(semantic_model["id"], "semantic_model")
            if source_files:
                _write_project_files(Path(compile_root) / semantic_folder_name, source_files)
            else:
                SemanticModelWriter(str(compile_root)).write(semantic_model.get("raw") or {}, project_name=semantic_model["name"])

        pages = []
        for page in detail["pages"]:
            visuals = page["visuals"]
            pages.append(_page_compile_payload(page, visuals, template_map, canvas_settings))

        report_payload = {
            "projectName": detail["name"],
            "reportFolderName": report_folder_name,
            "semanticModelFolderName": semantic_folder_name,
            "definitionPbir": {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
                "version": "4.0",
                "datasetReference": dataset_reference,
            },
            "report": _default_report_json_from_settings(canvas_settings),
            "pages": pages,
        }

        ReportWriter(str(compile_root)).write(
            report_payload,
            project_name=detail["name"],
            dataset_reference=dataset_reference,
        )

        pbip_path = compile_root / f"{detail['name']}.pbip"
        _safe_write_json(
            pbip_path,
            {
                "$schema": PBIP_SCHEMA_URL,
                "version": "1.0",
                "artifacts": [{"report": {"path": report_folder_name}}],
                "settings": {"enableAutoRecovery": True},
            },
        )

        archive_name = f"{detail['name']}.zip"
        archive_path = compile_root.parent / f"{detail['name']}-{request_id}.zip"
        _create_zip_archive(compile_root, archive_path)
        return archive_path, archive_name, compile_root
    except Exception:
        _safe_delete_path(compile_root)
        if archive_path:
            _safe_delete_path(archive_path)
        raise
