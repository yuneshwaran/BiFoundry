"""
Builds the datasetReference for definition.pbir and determines
whether a local SemanticModel folder needs to be generated.

Rules:
  source_kind == "powerbi"  →  byConnection (Power BI Service XMLA)
                              →  NO local SemanticModel folder
  source_kind == "local"    →  byPath (local model.bim / TMDL)
                              →  Local SemanticModel folder required
"""

XMLA_BASE = "powerbi://api.powerbi.com/v1.0/myorg"


def build_dataset_reference(source_row, source_kind):
    if source_kind == "powerbi":
        return _by_connection(source_row)
    return _by_path(source_row)


def needs_local_semantic_model(source_kind):
    return source_kind != "powerbi"


def _by_connection(source_row):
    workspace_name = source_row.get("workspace_name") or ""
    model_name = (
        source_row.get("semantic_model_name")
        or source_row.get("name")
        or ""
    )
    model_id = source_row.get("semantic_model_id") or ""

    connection_string = (
        f"Data Source={XMLA_BASE}/{workspace_name};"
        f"Initial Catalog={model_name};"
        f"Integrated Security=ClaimsToken;"
        f"semanticModelId={model_id}"
    )

    return {
        "byConnection": {
            "connectionString": connection_string
        }
    }


def _by_path(source_row):
    folder_name = (
        source_row.get("semantic_model_folder_name")
        or f"{source_row.get('name', 'Model')}.SemanticModel"
    )
    return {"byPath": {"path": f"../{folder_name}"}}
