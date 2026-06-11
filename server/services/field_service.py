from fastapi import HTTPException
from sqlalchemy import select

from database import engine, init_db
from utils.helpers import _as_dict
from repositories.semantic_repo import SemanticRepo


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


def _assert_source_semantic_model_exists(source_semantic_model_id):
    with engine.begin() as conn:
        repo = SemanticRepo(conn)
        row = repo.get_semantic_model(source_semantic_model_id)
        if not row:
            raise HTTPException(status_code=400, detail=f"Source semantic model {source_semantic_model_id} was not found.")
        return row


def _load_semantic_fields(dataset_id):
    with engine.begin() as conn:
        repo = SemanticRepo(conn)
        cached_fields = repo.get_dataset_fields(dataset_id)
        if cached_fields:
            return cached_fields

        semantic_model = repo.get_semantic_model(dataset_id)
        if not semantic_model:
            raise HTTPException(status_code=404, detail=f"Semantic model {dataset_id} was not found.")

        tables, fields, _relationships = _parse_field_options(semantic_model.get("raw") or {})
        repo.delete_dataset_fields(dataset_id)
        for field in fields:
            repo.insert_dataset_field(
                dataset_id=dataset_id,
                table_name=field.get("table"),
                field_name=field.get("name"),
                field_type=field.get("kind"),
                data_type=field.get("data_type"),
                dax_expression=field.get("dax_expression"),
            )
        return repo.get_dataset_fields(dataset_id)


def get_semantic_fields(source_project_id):
    init_db()
    source_semantic_model = _assert_source_semantic_model_exists(source_project_id)
    with engine.begin() as conn:
        repo = SemanticRepo(conn)
        semantic_model = repo.get_semantic_model(source_project_id)
        if not semantic_model:
            raise HTTPException(status_code=404, detail=f"Semantic model for source model {source_project_id} was not found.")
    tables, fields, relationships = _parse_field_options(semantic_model.get("raw") or {})
    return {
        "source_semantic_model_id": source_project_id,
        "source_semantic_model_name": source_semantic_model["name"],
        "tables": tables,
        "fields": fields,
        "relationships": relationships,
    }


def get_canvas_fields_v2(report_id):
    # relies on project detail lookup existing in project_service
    from services.project_service import _report_detail_v2

    detail = _report_detail_v2(report_id)
    with engine.begin() as conn:
        repo = SemanticRepo(conn)
        semantic_model = repo.get_semantic_model(detail["project_id"])
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
