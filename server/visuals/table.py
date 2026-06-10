import re
from typing import Any

from visuals.types import VisualBuildContext, VisualDefinition, VisualSlot


VISUAL_CONTAINER_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.9.0/schema.json"
)


def _artifact_name(visual: dict[str, Any]) -> str:
    visual_id = visual.get("id")
    if visual_id is not None:
        return f"visual_{visual_id}"
    raw_name = str(visual.get("name") or visual.get("visual_name") or "table").lower()
    safe_name = re.sub(r"[^a-z0-9]+", "_", raw_name).strip("_")
    return safe_name or "table"


def _field_projection(binding: dict[str, Any]) -> dict[str, Any]:
    table = binding["table"]
    name = binding["name"]
    kind = str(binding.get("kind") or "column").lower()
    field_type = "Measure" if kind == "measure" else "Column"
    field = {
        field_type: {
            "Property": name,
            "Expression": {
                "SourceRef": {
                    "Entity": table,
                }
            },
        }
    }
    return {
        "field": field,
        "queryRef": f"{table}.{name}",
        "nativeQueryRef": binding.get("label") or name,
        "active": True,
    }


def build_table_visual(visual: dict[str, Any], context: VisualBuildContext) -> dict[str, Any]:
    bindings = visual.get("bindings") or {}
    values = bindings.get("Values") or []
    if not isinstance(values, list):
        values = [values]

    projections = [
        _field_projection(binding)
        for binding in values
        if isinstance(binding, dict) and binding.get("table") and binding.get("name")
    ]
    if not projections:
        raise ValueError("Table visual requires at least one valid Values binding.")

    cell_width = context.page_width / context.grid_columns
    x = float(visual.get("x") or 0) * cell_width
    y = float(visual.get("y") or 0) * context.row_height
    width = float(visual.get("w") or TABLE_VISUAL.default_width) * cell_width
    height = float(visual.get("h") or TABLE_VISUAL.default_height) * context.row_height
    tab_order = float(visual.get("visual_order") or 0)
    artifact_name = _artifact_name(visual)

    return {
        "name": artifact_name,
        "$schema": VISUAL_CONTAINER_SCHEMA,
        "position": {
            "x": x,
            "y": y,
            "z": tab_order,
            "width": width,
            "height": height,
            "tabOrder": tab_order,
        },
        "visual": {
            "visualType": "tableEx",
            "query": {
                "queryState": {
                    "Values": {
                        "projections": projections,
                    }
                }
            },
            "drillFilterOtherVisuals": True,
        },
    }


TABLE_VISUAL = VisualDefinition(
    template_key="tableEx",
    name="Table",
    visual_type="tableEx",
    category="Table",
    icon="table_chart",
    description="Display selected semantic-model fields as detail columns.",
    default_width=5,
    default_height=4,
    slots=(
        VisualSlot(
            name="Values",
            role="Values",
            field_type="any",
            required=True,
            multi=True,
            description="Columns and measures displayed in the table.",
        ),
    ),
    builder=build_table_visual,
)
