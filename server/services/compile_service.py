import json
import uuid
import zipfile
from pathlib import Path
from fastapi import HTTPException

from config import WORK_ROOT
from database import engine, init_db
from pbip_generator.connection_builder import build_dataset_reference, needs_local_semantic_model
from pbip_generator.model_writer import SemanticModelWriter
from pbip_generator.report_writer import ReportWriter
from utils.helpers import _ensure_directory, _load_semantic_model_row, _safe_name, _safe_delete_path


def compile_draft(draft_id):
    from services.project_service import validate_draft, get_draft_detail, _synthesise_semantic_model_from_snapshot, _build_report_payload

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
