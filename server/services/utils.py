import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select

from models import (
    powerbi_semantic_models,
    semantic_models,
)


def _as_dict(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {}


def _ensure_directory(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def _safe_delete_path(path):
    target = Path(path)
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)
    elif target.exists():
        target.unlink(missing_ok=True)


def _safe_name(value, fallback="Draft"):
    text = (value or fallback).strip()
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text)
    text = text.rstrip(" .")
    return text or fallback


def _now():
    return datetime.now(timezone.utc).isoformat()


def _read_one(conn, stmt):
    row = conn.execute(stmt).first()
    return dict(row._mapping) if row else None


def _read_many(conn, stmt):
    return [dict(row._mapping) for row in conn.execute(stmt)]


def _load_semantic_model_row(conn, semantic_model_row_id):
    row = _read_one(conn, select(powerbi_semantic_models).where(powerbi_semantic_models.c.id == semantic_model_row_id))
    if row:
        return row, "powerbi"
    row = _read_one(conn, select(semantic_models).where(semantic_models.c.id == semantic_model_row_id))
    if row:
        return row, "local"
    return None, None


def _semantic_model_package_from_files(raw_dataset=None, file_rows=None):
    package = dict(raw_dataset or {})
    definition_files = dict(package.get("definitionFiles") or {})
    support_files = dict(package.get("supportFiles") or {})
    definition_pbism = package.get("definitionPbism")
    model = package.get("model")

    for file_row in file_rows or []:
        relative_path = (file_row or {}).get("relative_path") or ""
        content_kind = (file_row or {}).get("content_kind")
        json_content = (file_row or {}).get("json_content")
        text_content = (file_row or {}).get("text_content")
        binary_base64 = (file_row or {}).get("binary_base64")
        payload = None

        if content_kind == "json" and json_content is not None:
            payload = {"kind": "json", "content": json_content}
        elif content_kind == "text" and text_content is not None:
            payload = {"kind": "text", "content": text_content}
        elif content_kind == "binary" and binary_base64 is not None:
            payload = {"kind": "base64", "content": binary_base64}

        if not relative_path or payload is None:
            continue

        normalized_path = relative_path.replace("\\", "/")
        if normalized_path == "model.bim":
            if content_kind == "json" and isinstance(json_content, dict):
                model = json_content
            elif content_kind == "text" and isinstance(text_content, str):
                try:
                    model = json.loads(text_content)
                except json.JSONDecodeError:
                    pass
            continue

        if normalized_path == "definition.pbism":
            if content_kind == "json" and isinstance(json_content, dict):
                definition_pbism = json_content
            elif content_kind == "text" and isinstance(text_content, str):
                try:
                    definition_pbism = json.loads(text_content)
                except json.JSONDecodeError:
                    pass
            continue

        if normalized_path.startswith("definition/") and normalized_path.endswith(".tmdl"):
            definition_files[normalized_path.removeprefix("definition/")] = text_content or ""
            continue

        support_files[normalized_path] = payload

    if definition_files:
        package["definitionFiles"] = definition_files
    if support_files:
        package["supportFiles"] = support_files
    if definition_pbism is not None:
        package["definitionPbism"] = definition_pbism
    if model is not None:
        package["model"] = model

    return package
