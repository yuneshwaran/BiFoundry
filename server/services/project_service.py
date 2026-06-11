import json
import uuid
import zipfile
from copy import deepcopy
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import delete, select, update

from config import WORK_ROOT
from database import engine, init_db
from db_writer import DBLoader
from extractors.semantic_extractor import extract_tables_and_relationships
from models import (
    canvas_pages,
    canvas_reports,
    canvas_visuals,
    powerbi_workspaces,
    project_semantic_model_cache,
)
from pbip_generator.connection_builder import build_dataset_reference, needs_local_semantic_model
from pbip_generator.model_writer import SemanticModelWriter
from pbip_generator.report_writer import ReportWriter
from services.powerbi_client import iso_now
from services.powerbi_metadata_utils import extract_semantic_model_metadata
from services.powerbi_metadata_utils import extract_semantic_model_metadata_via_admin_scan
from services.powerbi_metadata_utils import extract_semantic_model_metadata_via_dax
from services.powerbi_service import (
    _load_latest_session_for_connection,
    _load_session_by_id,
    _session_client,
)
from services.utils import (
    _as_dict,
    _ensure_directory,
    _load_semantic_model_row,
    _now,
    _read_many,
    _read_one,
    _safe_delete_path,
    _safe_name,
)
from visuals import VisualBuildContext, build_visual, get_visual_definition, validate_visual_bindings


def _build_field_catalog(tables):
    catalog = []
    for table in tables or []:
        table_name = table.get("name") or table.get("tableName") or table.get("displayName") or "Table"
        for column in table.get("columns", []) or []:
            kind = column.get("kind") or column.get("type") or "column"
            catalog.append(
                {
                    "table": table_name,
                    "name": column.get("name") or column.get("columnName"),
                    "kind": kind,
                    "data_type": column.get("dataType") or column.get("type"),
                    "label": column.get("name") or column.get("columnName"),
                    "raw": column,
                }
            )
        for measure in table.get("measures", []) or []:
            catalog.append(
                {
                    "table": table_name,
                    "name": measure.get("name"),
                    "kind": "measure",
                    "data_type": measure.get("dataType") or "measure",
                    "label": measure.get("name"),
                    "raw": measure,
                }
            )
    return catalog


def _build_table_catalog(tables):
    return [
        {
            "name": table.get("name") or table.get("tableName") or table.get("displayName"),
            "raw": table,
        }
        for table in (tables or [])
        if table.get("name") or table.get("tableName") or table.get("displayName")
    ]


def _build_relationship_catalog(detail_payload):
    relationships = detail_payload.get("relationships") or detail_payload.get("model", {}).get("relationships") or []
    return [relationship for relationship in relationships if isinstance(relationship, dict)]


def _extract_powerbi_tables(raw_payload):
    if not isinstance(raw_payload, dict):
        return []
    candidates = [
        raw_payload.get("tables"),
        (raw_payload.get("semantic_model") or {}).get("tables"),
        (raw_payload.get("semantic_model") or {}).get("model", {}).get("tables"),
        raw_payload.get("model", {}).get("tables"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list) and candidate:
            return candidate
        if isinstance(candidate, dict):
            nested = candidate.get("value") or candidate.get("tables")
            if isinstance(nested, list) and nested:
                return nested
    return []


def _extract_powerbi_relationships(raw_payload):
    if not isinstance(raw_payload, dict):
        return []
    candidates = [
        raw_payload.get("relationships"),
        (raw_payload.get("semantic_model") or {}).get("relationships"),
        (raw_payload.get("semantic_model") or {}).get("model", {}).get("relationships"),
        raw_payload.get("model", {}).get("relationships"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list) and candidate:
            return [item for item in candidate if isinstance(item, dict)]
    return []


def _latest_project_cache(conn, project_id):
    return _read_one(
        conn,
        select(project_semantic_model_cache)
        .where(project_semantic_model_cache.c.project_id == project_id)
        .order_by(project_semantic_model_cache.c.cache_version.desc())
        .limit(1),
    )


def _sync_project_cache(conn, project_id, semantic_model_row_id, snapshot_payload):
    latest = _latest_project_cache(conn, project_id)
    next_version = (latest["cache_version"] if latest else 0) + 1
    result = conn.execute(
        project_semantic_model_cache.insert().values(
            project_id=project_id,
            semantic_model_row_id=semantic_model_row_id,
            cache_version=next_version,
            raw=snapshot_payload.get("raw"),
            field_catalog=snapshot_payload.get("field_catalog") or [],
            table_catalog=snapshot_payload.get("table_catalog") or [],
            relationship_catalog=snapshot_payload.get("relationship_catalog") or [],
            refreshed_at=_now(),
        )
    )
    cache_id = result.inserted_primary_key[0]
    return cache_id, next_version


def _build_powerbi_snapshot_payload(conn, report_row, source_row):
    connection_id = source_row.get("connection_id")
    session_row = _load_latest_session_for_connection(conn, connection_id) if connection_id else _load_session_by_id(conn, source_row["session_id"])
    client = _session_client(conn, session_row)
    workspace_id = source_row["workspace_id"]
    semantic_model_id = source_row["semantic_model_id"]
    workspace_name = source_row.get("workspace_name") or workspace_id
    semantic_model_name = source_row.get("semantic_model_name") or source_row.get("name") or semantic_model_id
    if connection_id:
        workspace_row = _read_one(
            conn,
            select(powerbi_workspaces).where(
                powerbi_workspaces.c.connection_id == connection_id,
                powerbi_workspaces.c.workspace_id == workspace_id,
            ),
        )
    else:
        workspace_row = _read_one(
            conn,
            select(powerbi_workspaces).where(
                powerbi_workspaces.c.session_id == session_row["id"],
                powerbi_workspaces.c.workspace_id == workspace_id,
            ),
        )
    semantic_model = client.get_semantic_model(workspace_id, semantic_model_id)
    admin_scan_metadata = None
    xmla_metadata = None
    dax_metadata = None
    try:
        admin_scan_metadata = extract_semantic_model_metadata_via_admin_scan(
            client=client,
            workspace_id=workspace_id,
            semantic_model_id=semantic_model_id,
            workspace_name=workspace_name,
            semantic_model_name=semantic_model_name,
        )
    except Exception as exc:
        admin_scan_metadata = {"error": str(exc)}
    if not (admin_scan_metadata and admin_scan_metadata.get("tables")):
        try:
            xmla_metadata = extract_semantic_model_metadata(
                workspace_name=workspace_name,
                semantic_model_name=semantic_model_name,
                access_token=session_row.get("access_token") if session_row else None,
                workspace_id=workspace_id,
                semantic_model_id=semantic_model_id,
            )
        except Exception as exc:
            xmla_metadata = {"error": str(exc)}
    if not ((admin_scan_metadata and admin_scan_metadata.get("tables")) or (xmla_metadata and xmla_metadata.get("tables"))):
        try:
            dax_metadata = extract_semantic_model_metadata_via_dax(
                client=client,
                workspace_id=workspace_id,
                semantic_model_id=semantic_model_id,
                workspace_name=workspace_name,
                semantic_model_name=semantic_model_name,
            )
        except Exception as exc:
            dax_metadata = {"error": str(exc)}
    try:
        tables = client.get_semantic_model_tables(workspace_id, semantic_model_id)
    except HTTPException:
        tables = []
    try:
        datasources = client.get_semantic_model_datasources(workspace_id, semantic_model_id)
    except HTTPException:
        datasources = []
    if admin_scan_metadata and admin_scan_metadata.get("tables"):
        tables = admin_scan_metadata.get("tables") or tables
    elif xmla_metadata and xmla_metadata.get("tables"):
        tables = xmla_metadata.get("tables") or tables
    elif dax_metadata and dax_metadata.get("tables"):
        tables = dax_metadata.get("tables") or tables
    if not tables:
        tables = _extract_powerbi_tables(source_row.get("raw") or {})
    relationships = []
    if admin_scan_metadata and admin_scan_metadata.get("relationships"):
        relationships = admin_scan_metadata.get("relationships") or []
    elif xmla_metadata and xmla_metadata.get("relationships"):
        relationships = xmla_metadata.get("relationships") or []
    elif dax_metadata and dax_metadata.get("relationships"):
        relationships = dax_metadata.get("relationships") or []
    if not relationships:
        relationships = _extract_powerbi_relationships({"semantic_model": semantic_model, "tables": tables}) or _extract_powerbi_relationships(source_row.get("raw") or {})
    raw_snapshot = {
        "project": {"id": report_row["id"], "name": report_row["name"]},
        "workspace": workspace_row or {"workspace_id": workspace_id, "workspace_name": source_row.get("workspace_name") or workspace_id},
        "semantic_model": semantic_model,
        "tables": tables,
        "datasources": datasources,
        "relationships": relationships,
        "admin_scan_metadata": admin_scan_metadata or {},
        "xmla_metadata": xmla_metadata or {},
        "dax_metadata": dax_metadata or {},
        "metadata_status": {
            "has_tables": bool(tables),
            "has_relationships": bool(relationships),
            "source": "admin_scan"
            if admin_scan_metadata and admin_scan_metadata.get("tables")
            else (
                "xmla"
                if xmla_metadata and xmla_metadata.get("tables")
                else ("dax_execute_queries" if dax_metadata and dax_metadata.get("tables") else ("rest" if tables else "fallback"))
            ),
        },
    }
    return {
        "raw": raw_snapshot,
        "field_catalog": _build_field_catalog(tables),
        "table_catalog": _build_table_catalog(tables),
        "relationship_catalog": relationships or _build_relationship_catalog(raw_snapshot),
    }


def _build_local_snapshot_payload(report_row, source_row):
    raw_dataset = source_row.get("raw") or {}
    tables, relationships = extract_tables_and_relationships(raw_dataset)
    if not tables and isinstance(raw_dataset.get("model"), dict):
        tables = raw_dataset.get("model", {}).get("tables") or []
    raw_snapshot = {
        "project": {"id": report_row["id"], "name": report_row["name"]},
        "semantic_model": raw_dataset,
        "tables": tables,
        "datasources": [],
    }
    return {
        "raw": raw_snapshot,
        "field_catalog": _build_field_catalog(tables),
        "table_catalog": _build_table_catalog(tables),
        "relationship_catalog": relationships or _build_relationship_catalog(raw_dataset),
    }


def _refresh_project_metadata_cache(conn, report_row, source_row, source_kind):
    if source_kind == "powerbi":
        snapshot_payload = _build_powerbi_snapshot_payload(conn, report_row, source_row)
        if not snapshot_payload.get("field_catalog"):
            debug_payload = (snapshot_payload.get("raw") or {}).get("metadata_status") or {}
            admin_scan_payload = ((snapshot_payload.get("raw") or {}).get("admin_scan_metadata") or {})
            xmla_error = ((snapshot_payload.get("raw") or {}).get("xmla_metadata") or {}).get("error")
            dax_payload = ((snapshot_payload.get("raw") or {}).get("dax_metadata") or {})
            detail = {
                "message": "No semantic metadata could be extracted from the selected Power BI semantic model.",
                "metadata_status": debug_payload,
                "admin_scan_error": admin_scan_payload.get("error"),
                "admin_scan_status": admin_scan_payload.get("scan_status") or admin_scan_payload.get("source"),
                "xmla_error": xmla_error,
                "dax_error": dax_payload.get("error"),
                "dax_query_failures": ((dax_payload.get("raw") or {}).get("query_failures") or {}),
                "hint": "Enable Power BI admin metadata scanning in the tenant, grant Tenant.Read.All or Tenant.ReadWrite.All to the app/user, or use a model with XMLA/build access.",
            }
            raise HTTPException(status_code=400, detail=detail)
    else:
        snapshot_payload = _build_local_snapshot_payload(report_row, source_row)
    cache_id, cache_version = _sync_project_cache(conn, report_row["id"], source_row["id"], snapshot_payload)
    report_raw = report_row.get("raw") or {}
    conn.execute(
        update(canvas_reports)
        .where(canvas_reports.c.id == report_row["id"])
        .values(
            raw={
                **report_raw,
                "project_cache_id": cache_id,
                "project_cache_version": cache_version,
                "source_reference": (source_row or {}).get("source_reference") or {},
            }
        )
    )
    updated_report_row = _get_report_row(conn, report_row["id"])
    cache_row = _latest_project_cache(conn, report_row["id"])
    return updated_report_row, cache_row or {}, cache_id, cache_version


def _select_snapshot_fields(snapshot_row):
    field_catalog = snapshot_row.get("field_catalog") if snapshot_row else []
    return field_catalog if isinstance(field_catalog, list) else []


def _field_key(field):
    return f"{field.get('table','')}.{field.get('name','')}".strip(".")


def _default_report_json(report_settings, canvas_settings):
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
            }
        },
        "objects": {
            "section": [
                {
                    "properties": {
                        "verticalAlignment": {
                            "expr": {"Literal": {"Value": "'Top'"}}
                        }
                    }
                }
            ]
        },
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
            "useDefaultAggregateDisplayName": True,
        },
    }


def _default_page_json(page_row):
    width = page_row.get("width") or 1280
    height = page_row.get("height") or 720
    page_name = page_row.get("page_name") or page_row.get("name") or f"Page{page_row.get('id')}"
    display_name = page_row.get("display_name") or page_name
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
        "name": page_name,
        "displayName": display_name,
        "displayOption": (page_row.get("settings") or {}).get("display_option") or "FitToPage",
        "width": width,
        "height": height,
    }


def _build_field_index(snapshot_row):
    index = {}
    for field in _select_snapshot_fields(snapshot_row):
        key = _field_key(field)
        if key and key != ".":
            index[key] = field
    return index


def _get_report_row(conn, report_id):
    return _read_one(conn, select(canvas_reports).where(canvas_reports.c.id == report_id))


def _get_page_row(conn, page_id):
    return _read_one(conn, select(canvas_pages).where(canvas_pages.c.id == page_id))


def _get_visual_row(conn, visual_id):
    return _read_one(conn, select(canvas_visuals).where(canvas_visuals.c.id == visual_id))


def _build_report_detail(conn, report_row):
    pages = _read_many(
        conn,
        select(canvas_pages)
        .where(canvas_pages.c.canvas_report_id == report_row["id"])
        .order_by(canvas_pages.c.page_order.asc(), canvas_pages.c.id.asc()),
    )
    page_payloads = []
    for page in pages:
        visuals = _read_many(
            conn,
            select(canvas_visuals)
            .where(canvas_visuals.c.canvas_page_id == page["id"])
            .order_by(canvas_visuals.c.visual_order.asc(), canvas_visuals.c.id.asc()),
        )
        page_payloads.append(
            {
                "id": page["id"],
                "canvas_report_id": page["canvas_report_id"],
                "page_name": page.get("page_name") or page.get("name"),
                "display_name": page.get("display_name") or page.get("name"),
                "page_order": page.get("page_order"),
                "name": page.get("name"),
                "width": page.get("width"),
                "height": page.get("height"),
                "raw": page.get("raw") or {},
                "visuals": visuals,
            }
        )
    source_row = None
    source_kind = None
    if report_row.get("source_semantic_model_id"):
        source_row, source_kind = _load_semantic_model_row(conn, report_row["source_semantic_model_id"])
    project_cache = _latest_project_cache(conn, report_row["id"])
    return {
        "id": report_row["id"],
        "name": report_row["name"],
        "description": report_row.get("description"),
        "source_semantic_model_id": report_row.get("source_semantic_model_id"),
        "source_semantic_model_name": report_row.get("source_semantic_model_name"),
        "canvas_settings": report_row.get("canvas_settings") or {},
        "report_settings": report_row.get("report_settings") or {},
        "raw": report_row.get("raw") or {},
        "source_reference": (source_row or {}).get("source_reference") or (report_row.get("raw") or {}).get("source_reference") or {},
        "source_snapshot": project_cache or {},
        "cache_version": (project_cache or {}).get("cache_version"),
        "pages": page_payloads,
    }


def list_drafts():
    init_db()
    with engine.begin() as conn:
        rows = _read_many(conn, select(canvas_reports).order_by(canvas_reports.c.id.desc()))
        results = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row.get("description"),
                    "source_semantic_model_id": row.get("source_semantic_model_id"),
                    "source_semantic_model_name": row.get("source_semantic_model_name"),
                    "canvas_settings": row.get("canvas_settings") or {},
                    "report_settings": row.get("report_settings") or {},
                    "raw": row.get("raw") or {},
                    "page_count": len(_read_many(conn, select(canvas_pages).where(canvas_pages.c.canvas_report_id == row["id"]))),
                }
            )
    return results


def create_draft(payload):
    init_db()
    payload = _as_dict(payload)
    name = (payload.get("name") or "").strip()
    source_semantic_model_id = payload.get("source_semantic_model_id")
    if not source_semantic_model_id:
        raise HTTPException(status_code=400, detail="A selected semantic model id is required.")
    canvas_settings = payload.get("canvas_settings") or {}
    report_settings = payload.get("report_settings") or {}
    raw = payload.get("raw") or {}
    pages = payload.get("pages") or []
    with engine.begin() as conn:
        source_row, source_kind = _load_semantic_model_row(conn, source_semantic_model_id)
        if not source_row:
            raise HTTPException(status_code=404, detail="Selected semantic model was not found.")
        if not name:
            name = source_row.get("semantic_model_name") or source_row.get("name") or f"Project {source_semantic_model_id}"
        report_id = DBLoader(conn).insert_canvas_report(
            name=name,
            description=payload.get("description"),
            source_semantic_model_id=source_semantic_model_id,
            source_semantic_model_name=source_row.get("semantic_model_name") or source_row.get("name"),
            canvas_settings=canvas_settings,
            report_settings=report_settings,
            raw={
                **raw,
                "source_reference": (source_row or {}).get("source_reference") or {},
                "source_kind": source_kind,
            },
        )
        loader = DBLoader(conn)
        for page_index, page in enumerate(pages):
            page = _as_dict(page)
            page_id = loader.insert_canvas_page(
                canvas_report_id=report_id,
                page_order=page.get("page_order", page_index),
                name=page.get("name") or page.get("page_name") or f"Page{page_index + 1}",
                display_name=page.get("display_name") or page.get("name") or page.get("page_name") or f"Page {page_index + 1}",
                width=page.get("width") or 1280,
                height=page.get("height") or 720,
                raw=page.get("raw") or {},
            )
            for visual_index, visual in enumerate(page.get("visuals") or []):
                visual = _as_dict(visual)
                template_key = visual.get("template_key") or visual.get("visual_type") or "visual"
                if not get_visual_definition(template_key):
                    raise HTTPException(status_code=400, detail=f"Unsupported visual template '{template_key}'.")
                loader.insert_canvas_visual(
                    canvas_page_id=page_id,
                    visual_order=visual.get("visual_order", visual_index),
                    template_key=template_key,
                    name=visual.get("name") or visual.get("visual_name") or f"Visual{visual_index + 1}",
                    x=int(visual.get("x") or 0),
                    y=int(visual.get("y") or 0),
                    w=int(visual.get("w") or 3),
                    h=int(visual.get("h") or 2),
                    bindings=visual.get("bindings") or {},
                    config=visual.get("config") or {},
                    raw=visual.get("raw") or {},
                )
        report_row = _get_report_row(conn, report_id)
        _refresh_project_metadata_cache(conn, report_row, source_row, source_kind)
    return get_draft_detail(report_id)


def get_draft_detail(draft_id):
    init_db()
    with engine.begin() as conn:
        report_row = _get_report_row(conn, draft_id)
        if not report_row:
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} was not found.")
        return _build_report_detail(conn, report_row)


def refresh_project_metadata(project_id):
    init_db()
    with engine.begin() as conn:
        report_row = _get_report_row(conn, project_id)
        if not report_row:
            raise HTTPException(status_code=404, detail=f"Project {project_id} was not found.")
        if not report_row.get("source_semantic_model_id"):
            raise HTTPException(status_code=400, detail="The project does not have a selected semantic model.")
        source_row, source_kind = _load_semantic_model_row(conn, report_row["source_semantic_model_id"])
        if not source_row:
            raise HTTPException(status_code=404, detail="Selected semantic model was not found.")
        report_row, cache_row, cache_id, cache_version = _refresh_project_metadata_cache(conn, report_row, source_row, source_kind)
    return {
        "project_id": project_id,
        "cache_id": cache_id,
        "cache_version": cache_version,
        "source_semantic_model_id": report_row.get("source_semantic_model_id"),
        "source_reference": (source_row or {}).get("source_reference") or {},
        "cache": cache_row or {},
    }


def update_draft(draft_id, payload):
    init_db()
    payload = _as_dict(payload)
    with engine.begin() as conn:
        report_row = _get_report_row(conn, draft_id)
        if not report_row:
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} was not found.")
        values = {}
        for key in ("name", "description", "canvas_settings", "report_settings"):
            if key in payload and payload[key] is not None:
                values[key] = payload[key]
        if "raw" in payload and payload["raw"] is not None:
            raw = deepcopy(report_row.get("raw") or {})
            raw.update(payload["raw"])
            values["raw"] = raw
        if "source_semantic_model_id" in payload and payload["source_semantic_model_id"] is not None:
            source_row, source_kind = _load_semantic_model_row(conn, payload["source_semantic_model_id"])
            if not source_row:
                raise HTTPException(status_code=404, detail="Selected semantic model was not found.")
            values["source_semantic_model_id"] = payload["source_semantic_model_id"]
            values["source_semantic_model_name"] = source_row.get("semantic_model_name") or source_row.get("name")
            raw = deepcopy(report_row.get("raw") or {})
            raw["source_reference"] = source_row.get("source_reference") or {}
            raw["source_kind"] = source_kind
            values["raw"] = raw
        if values:
            conn.execute(update(canvas_reports).where(canvas_reports.c.id == draft_id).values(**values))
    return get_draft_detail(draft_id)


def delete_draft(draft_id):
    init_db()
    with engine.begin() as conn:
        report_row = _get_report_row(conn, draft_id)
        if not report_row:
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} was not found.")
        page_ids = [row["id"] for row in _read_many(conn, select(canvas_pages.c.id).where(canvas_pages.c.canvas_report_id == draft_id))]
        if page_ids:
            conn.execute(delete(canvas_visuals).where(canvas_visuals.c.canvas_page_id.in_(page_ids)))
        conn.execute(delete(canvas_pages).where(canvas_pages.c.canvas_report_id == draft_id))
        conn.execute(delete(project_semantic_model_cache).where(project_semantic_model_cache.c.project_id == draft_id))
        conn.execute(delete(canvas_reports).where(canvas_reports.c.id == draft_id))
    return {"message": f"Draft '{report_row['name']}' deleted successfully.", "id": draft_id}


def create_page(draft_id, payload):
    init_db()
    payload = _as_dict(payload)
    with engine.begin() as conn:
        report_row = _get_report_row(conn, draft_id)
        if not report_row:
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} was not found.")
        page_id = DBLoader(conn).insert_canvas_page(
            canvas_report_id=draft_id,
            page_order=payload.get("page_order", 0),
            name=payload.get("name") or payload.get("page_name") or "Page",
            display_name=payload.get("display_name") or payload.get("name") or payload.get("page_name") or "Page",
            width=payload.get("width") or 1280,
            height=payload.get("height") or 720,
            raw=payload.get("raw") or {},
        )
        for visual_index, visual in enumerate(payload.get("visuals") or []):
            visual = _as_dict(visual)
            template_key = visual.get("template_key") or visual.get("visual_type") or "visual"
            if not get_visual_definition(template_key):
                raise HTTPException(status_code=400, detail=f"Unsupported visual template '{template_key}'.")
            DBLoader(conn).insert_canvas_visual(
                canvas_page_id=page_id,
                visual_order=visual.get("visual_order", visual_index),
                template_key=template_key,
                name=visual.get("name") or visual.get("visual_name") or f"Visual{visual_index + 1}",
                x=int(visual.get("x") or 0),
                y=int(visual.get("y") or 0),
                w=int(visual.get("w") or 3),
                h=int(visual.get("h") or 2),
                bindings=visual.get("bindings") or {},
                config=visual.get("config") or {},
                raw=visual.get("raw") or {},
            )
    return get_draft_detail(draft_id)


def update_page(page_id, payload):
    init_db()
    payload = _as_dict(payload)
    with engine.begin() as conn:
        page_row = _get_page_row(conn, page_id)
        if not page_row:
            raise HTTPException(status_code=404, detail=f"Page {page_id} was not found.")
        values = {}
        for key, column in (("name", "page_name"), ("display_name", "display_name"), ("width", "width"), ("height", "height"), ("page_order", "page_order")):
            if key in payload and payload[key] is not None:
                values[column] = payload[key]
                if column == "page_name":
                    values["name"] = payload[key]
        if "raw" in payload and payload["raw"] is not None:
            values["raw"] = payload["raw"]
        if values:
            conn.execute(update(canvas_pages).where(canvas_pages.c.id == page_id).values(**values))
    return get_draft_detail(page_row["canvas_report_id"])


def delete_page(page_id):
    init_db()
    with engine.begin() as conn:
        page_row = _get_page_row(conn, page_id)
        if not page_row:
            raise HTTPException(status_code=404, detail=f"Page {page_id} was not found.")
        conn.execute(delete(canvas_visuals).where(canvas_visuals.c.canvas_page_id == page_id))
        conn.execute(delete(canvas_pages).where(canvas_pages.c.id == page_id))
    return get_draft_detail(page_row["canvas_report_id"])


def create_visual(page_id, payload):
    init_db()
    payload = _as_dict(payload)
    template_key = payload.get("template_key") or payload.get("visual_type") or "visual"
    if not get_visual_definition(template_key):
        raise HTTPException(status_code=400, detail=f"Unsupported visual template '{template_key}'.")
    with engine.begin() as conn:
        page_row = _get_page_row(conn, page_id)
        if not page_row:
            raise HTTPException(status_code=404, detail=f"Page {page_id} was not found.")
        visual_id = DBLoader(conn).insert_canvas_visual(
            canvas_page_id=page_id,
            visual_order=payload.get("visual_order", 0),
            template_key=template_key,
            name=payload.get("name") or payload.get("visual_name") or "Visual",
            x=int(payload.get("x") or 0),
            y=int(payload.get("y") or 0),
            w=int(payload.get("w") or 3),
            h=int(payload.get("h") or 2),
            bindings=payload.get("bindings") or {},
            config=payload.get("config") or {},
            raw=payload.get("raw") or {},
        )
    return get_draft_detail(page_row["canvas_report_id"])


def update_visual(visual_id, payload):
    init_db()
    payload = _as_dict(payload)
    if payload.get("template_key") and not get_visual_definition(payload["template_key"]):
        raise HTTPException(status_code=400, detail=f"Unsupported visual template '{payload['template_key']}'.")
    with engine.begin() as conn:
        visual_row = _get_visual_row(conn, visual_id)
        if not visual_row:
            raise HTTPException(status_code=404, detail=f"Visual {visual_id} was not found.")
        values = {}
        for key in ("template_key", "name", "x", "y", "w", "h", "bindings", "config", "raw", "visual_order"):
            if key in payload and payload[key] is not None:
                values[key if key != "visual_order" else "visual_order"] = payload[key]
                if key == "name":
                    values["visual_name"] = payload[key]
        if values:
            conn.execute(update(canvas_visuals).where(canvas_visuals.c.id == visual_id).values(**values))
        page_row = _get_page_row(conn, visual_row["canvas_page_id"])
        return get_draft_detail(page_row["canvas_report_id"])


def delete_visual(visual_id):
    init_db()
    with engine.begin() as conn:
        visual_row = _get_visual_row(conn, visual_id)
        if not visual_row:
            raise HTTPException(status_code=404, detail=f"Visual {visual_id} was not found.")
        page_row = _get_page_row(conn, visual_row["canvas_page_id"])
        conn.execute(delete(canvas_visuals).where(canvas_visuals.c.id == visual_id))
    return get_draft_detail(page_row["canvas_report_id"])


def _validate_page(page_row):
    errors = []
    if not (page_row.get("width") or 0) > 0:
        errors.append({"scope": "page", "id": page_row["id"], "message": "Page width must be greater than zero."})
    if not (page_row.get("height") or 0) > 0:
        errors.append({"scope": "page", "id": page_row["id"], "message": "Page height must be greater than zero."})
    return errors


def _validate_visual(visual_row, field_index):
    errors = []
    if not (visual_row.get("w") or 0) > 0:
        errors.append({"scope": "visual", "id": visual_row["id"], "message": "Visual width must be greater than zero."})
    if not (visual_row.get("h") or 0) > 0:
        errors.append({"scope": "visual", "id": visual_row["id"], "message": "Visual height must be greater than zero."})
    definition = get_visual_definition(visual_row.get("template_key"))
    if not definition:
        errors.append(
            {
                "scope": "visual",
                "id": visual_row["id"],
                "message": f"Unsupported visual template '{visual_row.get('template_key')}'.",
            }
        )
        return errors

    for message in validate_visual_bindings(definition, visual_row, field_index):
        errors.append(
            {
                "scope": "visual",
                "id": visual_row["id"],
                "message": f"{message} Visual template: '{visual_row.get('template_key')}'.",
            }
        )
    return errors


def validate_draft(draft_id):
    detail = get_draft_detail(draft_id)
    errors = []
    source_snapshot = detail.get("source_snapshot") or {}
    field_index = {f"{field.get('table')}.{field.get('name')}": field for field in (source_snapshot.get("field_catalog") or []) if field.get("table") and field.get("name")}
    if not field_index:
        errors.append({"scope": "draft", "id": draft_id, "message": "No semantic metadata snapshot is available for validation."})
    for page in detail.get("pages") or []:
        errors.extend(_validate_page(page))
        for visual in page.get("visuals") or []:
            errors.extend(_validate_visual(visual, field_index))
    return {"draft_id": draft_id, "valid": not errors, "errors": errors, "field_count": len(field_index)}


def get_draft_fields(draft_id):
    detail = get_draft_detail(draft_id)
    snapshot = detail.get("source_snapshot") or {}
    tables = {}
    for field in snapshot.get("field_catalog") or []:
        table_name = field.get("table") or "Unknown"
        tables.setdefault(table_name, []).append(field)
    return {
        "draft_id": draft_id,
        "source_semantic_model_id": detail.get("source_semantic_model_id"),
        "source_semantic_model_name": detail.get("source_semantic_model_name"),
        "tables": [{"table": table_name, "fields": fields} for table_name, fields in sorted(tables.items())],
        "fields": snapshot.get("field_catalog") or [],
        "relationships": snapshot.get("relationship_catalog") or [],
        "debug": {
            "cache_version": detail.get("cache_version"),
            "metadata_status": ((snapshot.get("raw") or {}).get("metadata_status") or {}),
            "admin_scan_error": ((snapshot.get("raw") or {}).get("admin_scan_metadata") or {}).get("error"),
            "admin_scan_status": ((snapshot.get("raw") or {}).get("admin_scan_metadata") or {}).get("scan_status")
            or ((snapshot.get("raw") or {}).get("admin_scan_metadata") or {}).get("source"),
            "xmla_error": ((snapshot.get("raw") or {}).get("xmla_metadata") or {}).get("error"),
            "dax_error": ((snapshot.get("raw") or {}).get("dax_metadata") or {}).get("error"),
            "dax_query_failures": (((snapshot.get("raw") or {}).get("dax_metadata") or {}).get("raw") or {}).get("query_failures") or {},
        },
    }


# def _synthesise_semantic_model_from_snapshot(source_name, snapshot):
#     tables = {}
#     for field in snapshot.get("field_catalog") or []:
#         table_name = field.get("table") or "Table"
#         table = tables.setdefault(
#             table_name,
#             {
#                 "name": table_name,
#                 "columns": [],
#                 "measures": [],
#             },
#         )
#         payload = {
#             "name": field.get("name"),
#             "dataType": field.get("data_type"),
#         }
#         if field.get("kind") == "measure":
#             table["measures"].append(payload)
#         else:
#             table["columns"].append(payload)
#     return {
#         "model": {
#             "name": source_name,
#             "compatibilityLevel": 1601,
#             "tables": list(tables.values()),
#             "relationships": snapshot.get("relationship_catalog") or [],
#         }
#     }
    
def _synthesise_semantic_model_from_snapshot(source_name, snapshot):
    tables = {}
    for field in snapshot.get("field_catalog") or []:
        table_name = field.get("table") or "Table"
        table = tables.setdefault(table_name, {
            "name": table_name,
            "columns": [],
            "measures": [],
        })
        payload = {
            "name": field.get("name"),
            "dataType": field.get("data_type"),
        }
        if field.get("kind") == "measure":
            table["measures"].append(payload)
        else:
            table["columns"].append(payload)

    # Return as raw_dataset shape — SemanticModelWriter reads raw_dataset.get("model")
    # and then wraps it with name + compatibilityLevel at the top level
    return {
        "name": source_name,
        "compatibilityLevel": 1601,
        "model": {
            "tables": list(tables.values()),
            "relationships": snapshot.get("relationship_catalog") or [],
        }
    }

def _build_report_payload(detail, semantic_folder_name, dataset_reference):
    report_settings = detail.get("report_settings") or {}
    canvas_settings = detail.get("canvas_settings") or {}
    report_folder_name = f"{_safe_name(detail['name'], fallback='Draft')}.Report"
    
    definition_pbir = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": dataset_reference,
    }

    pages = []
    for page in detail.get("pages") or []:
        visuals = []
        for visual in page.get("visuals") or []:
            context = VisualBuildContext(
                page_width=page.get("width") or canvas_settings.get("width") or 1280,
                page_height=page.get("height") or canvas_settings.get("height") or 720,
            )
            try:
                visual_json = build_visual(visual.get("template_key"), visual, context)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            visuals.append(
                {
                    "name": visual_json["name"],
                    "visual": visual_json,
                }
            )
        pages.append(
            {
                "name": page.get("name") or page.get("page_name") or f"Page{page.get('id')}",
                "page": _default_page_json(page),
                "visuals": visuals,
            }
        )
    return {
        "projectName": detail["name"],
        "reportFolderName": report_folder_name,
        "semanticModelFolderName": semantic_folder_name,
        "definitionPbir": definition_pbir,
        "report": _default_report_json(report_settings, canvas_settings),
        "pages": pages,
    }


def compile_draft(draft_id):
    validation = validate_draft(draft_id)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail={"message": "Draft validation failed.", "errors": validation["errors"]})
    init_db()
    compile_id = uuid.uuid4().hex
    compile_root = Path(WORK_ROOT) / "draft-compiles" / compile_id
    _ensure_directory(compile_root)
    with engine.begin() as conn:
        detail = get_draft_detail(draft_id)
        source_snapshot = detail.get("source_snapshot") or {}
        if not source_snapshot.get("field_catalog"):
            raise HTTPException(status_code=400, detail="Refresh the project metadata cache before compiling.")
        source_name = _safe_name(detail.get("source_semantic_model_name") or detail["name"], fallback=detail["name"])
        source_row, source_kind = _load_semantic_model_row(conn, detail["source_semantic_model_id"])

        dataset_reference = build_dataset_reference(source_row, source_kind)

        if needs_local_semantic_model(source_kind):
            semantic_folder_name = f"{source_name}.SemanticModel"
            dataset_payload = _synthesise_semantic_model_from_snapshot(source_name, source_snapshot)
            SemanticModelWriter(str(compile_root)).write(dataset_payload, project_name=source_name)
        else:
            semantic_folder_name = None

        report_payload = _build_report_payload(detail, semantic_folder_name, dataset_reference)
        ReportWriter(str(compile_root)).write(
            report_payload,
            project_name=detail["name"],
            dataset_reference=dataset_reference,
        )
        safe_report_name = _safe_name(detail["name"], fallback="Draft")
        pbip_path = compile_root / f"{safe_report_name}.pbip"
        with open(pbip_path, "w", encoding="utf-8") as file_handle:
            json.dump(
                {
                    "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
                    "version": "1.0",
                    "artifacts": [{"report": {"path": f"{safe_report_name}.Report"}}],
                    "settings": {"enableAutoRecovery": True},
                },
                file_handle,
                indent=2,
                ensure_ascii=False,
            )
    archive_name = f"{_safe_name(detail['name'], fallback='Draft')}.zip"
    archive_path = compile_root.parent / f"{_safe_name(detail['name'], fallback='Draft')}-{compile_id}.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_handle:
        for file_path in compile_root.rglob("*"):
            if file_path.is_file():
                zip_handle.write(file_path, arcname=file_path.relative_to(compile_root))
    return str(archive_path), archive_name, str(compile_root)


def cleanup_compile_output(compile_root, archive_path):
    _safe_delete_path(compile_root)
    _safe_delete_path(archive_path)
