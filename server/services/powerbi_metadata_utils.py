from __future__ import annotations

import time

from fastapi import HTTPException


def _normalize_name(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_row_key(key):
    text = str(key or "").strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    if "." in text:
        text = text.split(".")[-1]
    return text.strip().lower().replace(" ", "").replace("_", "")


def _row_value(row, *keys):
    normalized = {_normalize_row_key(key): value for key, value in (row or {}).items()}
    for key in keys:
        probe = _normalize_row_key(key)
        if probe in normalized and normalized[probe] is not None:
            return normalized[probe]
    return None


def extract_semantic_model_metadata(*args, **kwargs) -> dict:
    return {
        "tables": [],
        "relationships": [],
        "raw": {},
        "error": None,
        "disabled": True,
        "source": "disabled_xmla",
    }


def _normalize_scan_name(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _find_scanned_workspace(scan_result: dict, workspace_id: str):
    workspaces = scan_result.get("workspaces") or []
    for workspace in workspaces:
        if not isinstance(workspace, dict):
            continue
        if workspace_id and str(workspace.get("id") or workspace.get("workspaceId") or "").strip() == str(workspace_id).strip():
            return workspace
        if workspace_id and str(workspace.get("name") or "").strip() == str(workspace_id).strip():
            return workspace
    return None


def _find_scanned_dataset(workspace_info: dict, semantic_model_id: str):
    datasets = workspace_info.get("datasets") or []
    for dataset in datasets:
        if not isinstance(dataset, dict):
            continue
        candidate_id = (
            dataset.get("id")
            or dataset.get("objectId")
            or dataset.get("datasetId")
            or dataset.get("semanticModelId")
        )
        if candidate_id and str(candidate_id).strip() == str(semantic_model_id).strip():
            return dataset
    return None


def _normalize_scan_tables(dataset_info: dict) -> list[dict]:
    tables = []
    for table in dataset_info.get("tables") or []:
        if not isinstance(table, dict):
            continue
        table_name = _normalize_scan_name(table.get("name") or table.get("displayName") or table.get("tableName"))
        if not table_name:
            continue
        normalized_table = {
            "name": table_name,
            "description": table.get("description"),
            "isHidden": bool(table.get("isHidden") or False),
            "columns": [],
            "measures": [],
            "raw": table,
            "source": "admin_scan",
        }
        for column in table.get("columns") or []:
            if not isinstance(column, dict):
                continue
            column_name = _normalize_scan_name(column.get("name") or column.get("displayName") or column.get("caption"))
            if not column_name:
                continue
            expression = column.get("expression") or column.get("columnExpression")
            column_type = _normalize_scan_name(column.get("type") or column.get("kind"))
            normalized_table["columns"].append(
                {
                    "id": column.get("id") or column.get("columnId"),
                    "name": column_name,
                    "dataType": column.get("dataType") or column.get("type") or column.get("columnType"),
                    "type": "calculated_column" if expression else (column_type or "column"),
                    "sourceColumn": column.get("sourceColumn") or column.get("sourceColumnName"),
                    "expression": expression,
                    "isHidden": bool(column.get("isHidden") or False),
                    "displayFolder": column.get("displayFolder"),
                    "raw": column,
                }
            )
        for measure in table.get("measures") or []:
            if not isinstance(measure, dict):
                continue
            measure_name = _normalize_scan_name(measure.get("name") or measure.get("displayName") or measure.get("caption"))
            if not measure_name:
                continue
            normalized_table["measures"].append(
                {
                    "id": measure.get("id") or measure.get("measureId"),
                    "name": measure_name,
                    "dataType": measure.get("dataType") or measure.get("type") or "measure",
                    "expression": measure.get("expression"),
                    "isHidden": bool(measure.get("isHidden") or False),
                    "displayFolder": measure.get("displayFolder"),
                    "formatString": measure.get("formatString"),
                    "raw": measure,
                }
            )
        tables.append(normalized_table)
    return tables


def _normalize_scan_relationships(dataset_info: dict) -> list[dict]:
    relationships = []
    for relationship in dataset_info.get("relationships") or []:
        if not isinstance(relationship, dict):
            continue
        from_table = _normalize_scan_name(
            relationship.get("fromTable")
            or relationship.get("fromTableName")
            or relationship.get("fromObject")
        )
        to_table = _normalize_scan_name(
            relationship.get("toTable")
            or relationship.get("toTableName")
            or relationship.get("toObject")
        )
        from_column = _normalize_scan_name(relationship.get("fromColumn") or relationship.get("fromColumnName"))
        to_column = _normalize_scan_name(relationship.get("toColumn") or relationship.get("toColumnName"))
        if not (from_table and to_table and from_column and to_column):
            continue
        relationships.append(
            {
                "name": _normalize_scan_name(relationship.get("name")) or f"{from_table}->{to_table}",
                "fromTable": from_table,
                "fromColumn": from_column,
                "toTable": to_table,
                "toColumn": to_column,
                "isActive": bool(relationship.get("isActive") or False),
                "crossFilteringBehavior": relationship.get("crossFilteringBehavior"),
                "cardinality": relationship.get("cardinality"),
                "raw": relationship,
                "source": "admin_scan",
            }
        )
    return relationships


def extract_semantic_model_metadata_via_admin_scan(
    client,
    workspace_id: str,
    semantic_model_id: str,
    workspace_name: str,
    semantic_model_name: str,
    *,
    timeout_seconds: int = 45,
    poll_interval_seconds: float = 2.0,
) -> dict:
    scan_start = client.post_workspace_info_scan(
        [workspace_id],
        lineage=True,
        datasource_details=True,
        dataset_schema=True,
        dataset_expressions=True,
        get_artifact_users=False,
    )
    scan_id = scan_start.get("id") or scan_start.get("scanId") or scan_start.get("scan_id")
    if not scan_id:
        return {
            "workspace_name": workspace_name,
            "semantic_model_name": semantic_model_name,
            "tables": [],
            "relationships": [],
            "raw": {"scan_start": scan_start},
            "error": "Admin metadata scan did not return a scan id.",
            "source": "admin_scan",
        }

    scan_status = {}
    deadline = time.monotonic() + max(1, int(timeout_seconds))
    while True:
        scan_status = client.get_workspace_scan_status(scan_id)
        status_value = str(scan_status.get("status") or "").strip().lower()
        if status_value in {"succeeded", "failed", "cancelled"}:
            break
        if time.monotonic() >= deadline:
            return {
                "workspace_name": workspace_name,
                "semantic_model_name": semantic_model_name,
                "tables": [],
                "relationships": [],
                "raw": {
                    "scan_start": scan_start,
                    "scan_status": scan_status,
                },
                "error": "Admin metadata scan timed out before completion.",
                "source": "admin_scan",
                "scan_id": scan_id,
            }
        time.sleep(max(0.25, float(poll_interval_seconds)))

    status_value = str(scan_status.get("status") or "").strip().lower()
    if status_value != "succeeded":
        return {
            "workspace_name": workspace_name,
            "semantic_model_name": semantic_model_name,
            "tables": [],
            "relationships": [],
            "raw": {
                "scan_start": scan_start,
                "scan_status": scan_status,
            },
            "error": scan_status.get("error") or f"Admin metadata scan ended with status '{scan_status.get('status')}'.",
            "source": "admin_scan",
            "scan_id": scan_id,
        }

    scan_result = client.get_workspace_scan_result(scan_id)
    workspace_info = _find_scanned_workspace(scan_result, workspace_id) or {}
    dataset_info = _find_scanned_dataset(workspace_info, semantic_model_id) or {}
    if not dataset_info:
        return {
            "workspace_name": workspace_name,
            "semantic_model_name": semantic_model_name,
            "tables": [],
            "relationships": [],
            "raw": {
                "scan_start": scan_start,
                "scan_status": scan_status,
                "scan_result": scan_result,
                "workspace": workspace_info,
            },
            "error": "Admin metadata scan completed but the selected semantic model was not present in the result.",
            "source": "admin_scan",
            "scan_id": scan_id,
        }

    tables = _normalize_scan_tables(dataset_info)
    relationships = _normalize_scan_relationships(dataset_info)
    return {
        "workspace_name": workspace_name,
        "semantic_model_name": semantic_model_name,
        "tables": tables,
        "relationships": relationships,
        "raw": {
            "scan_start": scan_start,
            "scan_status": scan_status,
            "scan_result": scan_result,
            "workspace": workspace_info,
            "dataset": dataset_info,
        },
        "source": "admin_scan",
        "scan_id": scan_id,
        "scan_status": scan_status.get("status"),
    }


def _normalize_execute_queries_rowsets(workspace_name: str, semantic_model_name: str, rowsets: dict) -> dict:
    tables_by_name = {}

    for table_row in rowsets.get("tables") or []:
        table_name = _normalize_name(
            _row_value(table_row, "Name", "Table", "TableName", "ExplicitName", "Caption")
        )
        if not table_name:
            continue
        tables_by_name[table_name] = {
            "id": _row_value(table_row, "ID", "TableID"),
            "name": table_name,
            "description": _row_value(table_row, "Description"),
            "isHidden": bool(_row_value(table_row, "IsHidden") or False),
            "columns": [],
            "measures": [],
            "raw": table_row,
        }

    for column_row in rowsets.get("columns") or []:
        table_name = _normalize_name(_row_value(column_row, "Table", "TableName", "Parent"))
        column_name = _normalize_name(_row_value(column_row, "Name", "ExplicitName", "Caption"))
        if not table_name or not column_name:
            continue
        table = tables_by_name.setdefault(
            table_name,
            {
                "id": None,
                "name": table_name,
                "description": None,
                "isHidden": False,
                "columns": [],
                "measures": [],
                "raw": {},
            },
        )
        expression = _row_value(column_row, "Expression", "ColumnExpression")
        column_type = _normalize_name(_row_value(column_row, "Type", "ColumnType"))
        semantic_kind = "calculated_column" if expression or column_type == "calculated" else "column"
        table["columns"].append(
            {
                "id": _row_value(column_row, "ID", "ColumnID"),
                "name": column_name,
                "dataType": _row_value(column_row, "DataType", "Type"),
                "type": semantic_kind,
                "sourceColumn": _row_value(column_row, "SourceColumn", "SourceColumnName"),
                "expression": expression,
                "isHidden": bool(_row_value(column_row, "IsHidden") or False),
                "displayFolder": _row_value(column_row, "DisplayFolder"),
                "raw": column_row,
            }
        )

    for measure_row in rowsets.get("measures") or []:
        table_name = _normalize_name(_row_value(measure_row, "Table", "TableName", "Parent"))
        measure_name = _normalize_name(_row_value(measure_row, "Name", "ExplicitName", "Caption"))
        if not table_name or not measure_name:
            continue
        table = tables_by_name.setdefault(
            table_name,
            {
                "id": None,
                "name": table_name,
                "description": None,
                "isHidden": False,
                "columns": [],
                "measures": [],
                "raw": {},
            },
        )
        table["measures"].append(
            {
                "id": _row_value(measure_row, "ID", "MeasureID"),
                "name": measure_name,
                "dataType": _row_value(measure_row, "DataType", "Type"),
                "expression": _row_value(measure_row, "Expression"),
                "isHidden": bool(_row_value(measure_row, "IsHidden") or False),
                "displayFolder": _row_value(measure_row, "DisplayFolder"),
                "raw": measure_row,
            }
        )

    relationships = []
    for relationship_row in rowsets.get("relationships") or []:
        from_table = _normalize_name(_row_value(relationship_row, "FromTable", "FromTableName"))
        to_table = _normalize_name(_row_value(relationship_row, "ToTable", "ToTableName"))
        from_column = _normalize_name(_row_value(relationship_row, "FromColumn", "FromColumnName"))
        to_column = _normalize_name(_row_value(relationship_row, "ToColumn", "ToColumnName"))
        if not (from_table and to_table and from_column and to_column):
            continue
        relationships.append(
            {
                "name": _normalize_name(_row_value(relationship_row, "Name")) or f"{from_table}->{to_table}",
                "fromTable": from_table,
                "fromColumn": from_column,
                "toTable": to_table,
                "toColumn": to_column,
                "isActive": bool(_row_value(relationship_row, "IsActive") or False),
                "crossFilteringBehavior": _row_value(relationship_row, "CrossFilteringBehavior"),
                "raw": relationship_row,
            }
        )

    return {
        "workspace_name": workspace_name,
        "semantic_model_name": semantic_model_name,
        "tables": list(tables_by_name.values()),
        "relationships": relationships,
        "raw": rowsets,
    }


def extract_semantic_model_metadata_via_dax(client, workspace_id: str, semantic_model_id: str, workspace_name: str, semantic_model_name: str) -> dict:
    queries = {
        "tables": "EVALUATE INFO.TABLES()",
        "columns": "EVALUATE INFO.COLUMNS()",
        "measures": "EVALUATE INFO.MEASURES()",
        "relationships": "EVALUATE INFO.RELATIONSHIPS()",
    }
    rowsets = {}
    failures = {}
    for key, query in queries.items():
        try:
            rowsets[key] = client.execute_semantic_model_query(workspace_id, semantic_model_id, query)
        except HTTPException as exc:
            failures[key] = exc.detail
            rowsets[key] = []
        except Exception as exc:
            failures[key] = str(exc)
            rowsets[key] = []
    normalized = _normalize_execute_queries_rowsets(workspace_name, semantic_model_name, rowsets)
    normalized["raw"] = {
        **(normalized.get("raw") or {}),
        "query_failures": failures,
        "query_source": "executeQueries",
    }
    return normalized
