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
    raw_name = str(visual.get("name") or visual.get("visual_name") or "slicer").lower()
    safe_name = re.sub(r"[^a-z0-9]+", "_", raw_name).strip("_")
    return safe_name or "slicer"


def _field_projection(binding: dict[str, Any]) -> dict[str, Any]:
    table = binding["table"]
    name = binding["name"]
    kind = str(binding.get("kind") or "column").lower()
    field_type = "Measure" if kind == "measure" else "Column"
    return {
        "field": {
            field_type: {
                "Property": name,
                "Expression": {"SourceRef": {"Entity": table}},
            }
        },
        "queryRef": f"{table}.{name}",
        "nativeQueryRef": binding.get("label") or name,
        "active": True,
    }


def build_slicer_visual(visual: dict[str, Any], context: VisualBuildContext) -> dict[str, Any]:
    bindings = visual.get("bindings") or {}

    field_binding = bindings.get("Field")
    if not field_binding or not isinstance(field_binding, dict) or not field_binding.get("table"):
        raise ValueError("Slicer requires a Field binding.")

    cell_width = context.page_width / context.grid_columns
    x = float(visual.get("x") or 0) * cell_width
    y = float(visual.get("y") or 0) * context.row_height
    width = float(visual.get("w") or SLICER_VISUAL.default_width) * cell_width
    height = float(visual.get("h") or SLICER_VISUAL.default_height) * context.row_height
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
            "visualType": "slicer",
            "query": {
                "queryState": {
                    "Field": {
                        "projections": [_field_projection(field_binding)]
                    }
                }
            },
            # Slicer default style: vertical list
            "objects": {
                "data": [
                    {
                        "properties": {
                            "mode": {
                                "expr": {
                                    "Literal": {"Value": "'Basic'"}
                                }
                            }
                        }
                    }
                ]
            },
            "drillFilterOtherVisuals": True,
        },
    }


SLICER_VISUAL = VisualDefinition(
    template_key="slicer",
    name="Slicer",
    visual_type="slicer",
    category="Filter",
    icon="filter_alt",
    description="Filter the report page by selecting field values.",
    default_width=2,
    default_height=3,
    slots=(
        VisualSlot(
            name="Field",
            role="Field",
            field_type="column",
            required=True,
            multi=False,
            description="The column to filter on.",
        ),
    ),
    builder=build_slicer_visual,
)
