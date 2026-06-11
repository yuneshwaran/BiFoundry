import json
import shutil
import uuid
from copy import deepcopy
from pathlib import Path

from fastapi import HTTPException

from config import WORK_ROOT
from database import engine, init_db
from repositories.template_repo import TemplateRepo
from extractors.report_extractor import ReportExtractor


from utils.helpers import _ensure_directory


def _unzip_archive(archive_path, destination):
    destination_path = Path(destination).resolve()
    _ensure_directory(destination_path)
    import zipfile

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
    import re

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
    if not isinstance(default_visual_json.get("query"), dict):
        default_visual_json["query"] = {"queryState": {"projections": {}}}
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
                slot("Y Axis / Value", "Y", "any", True, False, "Choose the measure to plot"),
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
    ]


def seed_visual_templates():
    init_db()
    with engine.begin() as conn:
        repo = TemplateRepo(conn)
        existing_by_key = {row.get("template_key"): row for row in repo.get_visual_templates()}
        for template in _default_visual_templates():
            existing = existing_by_key.get(template["template_key"])
            if existing:
                repo.update_visual_template(
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

            repo.insert_visual_template(
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
        repo = TemplateRepo(conn)
        templates = [template for template in repo.get_visual_templates() if str(template.get("is_active", "1")) == "1"]
        if not templates:
            seed_visual_templates()
            templates = [template for template in repo.get_visual_templates() if str(template.get("is_active", "1")) == "1"]
        return [
            {
                **template,
                "slot_definitions": template.get("slot_definitions") or _slot_definitions_from_visual_json(template),
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
            repo = TemplateRepo(conn)
            for template in templates:
                existing = repo.get_visual_template_by_key(template["template_key"])
                if existing:
                    repo.update_visual_template(
                        existing["id"],
                        template_key=template["template_key"],
                        name=template["name"],
                        category=template.get("category"),
                        icon=template.get("icon"),
                        description=template.get("description"),
                        default_width=template.get("default_width"),
                        default_height=template.get("default_height"),
                        required_slots=template.get("required_slots"),
                        optional_slots=template.get("optional_slots"),
                        default_visual_json=template.get("default_visual_json"),
                        visual_type=template.get("visual_type"),
                        slot_definitions=template.get("slot_definitions"),
                        default_format=template.get("default_format"),
                        is_active=template.get("is_active"),
                    )
                    updated += 1
                else:
                    repo.insert_visual_template(
                        template_key=template["template_key"],
                        name=template["name"],
                        category=template.get("category"),
                        icon=template.get("icon"),
                        description=template.get("description"),
                        default_width=template.get("default_width"),
                        default_height=template.get("default_height"),
                        required_slots=template.get("required_slots"),
                        optional_slots=template.get("optional_slots"),
                        default_visual_json=template.get("default_visual_json"),
                        visual_type=template.get("visual_type"),
                        slot_definitions=template.get("slot_definitions"),
                        default_format=template.get("default_format"),
                        is_active=template.get("is_active"),
                    )
                    created += 1
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "templates": templates,
    }