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
    raw_name = str(visual.get("name") or visual.get("visual_name") or "pie").lower()
    safe_name = re.sub(r"[^a-z0-9]+", "_", raw_name).strip("_")
    return safe_name or "pie"


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


def build_pie_visual(visual: dict[str, Any], context: VisualBuildContext) -> dict[str, Any]:
    bindings = visual.get("bindings") or {}

    category = bindings.get("Category")
    values = bindings.get("Values")

    if not category or not isinstance(category, dict) or not category.get("table"):
        raise ValueError("Pie chart requires a Category binding.")
    if not values or not isinstance(values, dict) or not values.get("table"):
        raise ValueError("Pie chart requires a Values binding.")

    category_projection = _field_projection(category)
    values_projection = _field_projection(values)

    # Optional tooltip
    tooltip_bindings = bindings.get("Tooltips") or []
    if isinstance(tooltip_bindings, dict):
        tooltip_bindings = [tooltip_bindings]
    tooltip_projections = [
        _field_projection(b)
        for b in tooltip_bindings
        if isinstance(b, dict) and b.get("table") and b.get("name")
    ]

    cell_width = context.page_width / context.grid_columns
    x = float(visual.get("x") or 0) * cell_width
    y = float(visual.get("y") or 0) * context.row_height
    width = float(visual.get("w") or PIE_VISUAL.default_width) * cell_width
    height = float(visual.get("h") or PIE_VISUAL.default_height) * context.row_height
    tab_order = float(visual.get("visual_order") or 0)
    artifact_name = _artifact_name(visual)

    query_state = {
        "Category": {"projections": [category_projection]},
        "Y": {"projections": [values_projection]},
    }
    if tooltip_projections:
        query_state["Tooltips"] = {"projections": tooltip_projections}

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
            "visualType": "donutChart",
            "query": {"queryState": query_state},
            "drillFilterOtherVisuals": True,
        },
    }


PIE_VISUAL = VisualDefinition(
    template_key="donutChart",
    name="Pie / Donut Chart",
    visual_type="donutChart",
    category="Chart",
    icon="pie_chart",
    description="Show part-to-whole proportions across categories.",
    default_width=3,
    default_height=3,
    slots=(
        VisualSlot(
            name="Category",
            role="Category",
            field_type="column",
            required=True,
            multi=False,
            description="The slice label column.",
        ),
        VisualSlot(
            name="Values",
            role="Values",
            field_type="measure",
            required=True,
            multi=False,
            description="The measure that determines slice size.",
        ),
        VisualSlot(
            name="Tooltips",
            role="Tooltips",
            field_type="any",
            required=False,
            multi=True,
            description="Optional extra fields shown on hover.",
        ),
    ),
    builder=build_pie_visual,
)
