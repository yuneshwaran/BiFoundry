import re
from typing import Any

from visuals.types import VisualBuildContext, VisualDefinition, VisualSlot

VISUAL_CONTAINER_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.9.0/schema.json"
)


def _artifact_name(visual: dict[str, Any], prefix: str = "bar") -> str:
    visual_id = visual.get("id")
    if visual_id is not None:
        return f"visual_{visual_id}"
    raw_name = str(visual.get("name") or visual.get("visual_name") or prefix).lower()
    safe_name = re.sub(r"[^a-z0-9]+", "_", raw_name).strip("_")
    return safe_name or prefix


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


def _build_bar_like(visual_type: str, visual: dict[str, Any], context: VisualBuildContext) -> dict[str, Any]:
    bindings = visual.get("bindings") or {}

    category = bindings.get("Category")
    y_binding = bindings.get("Y")

    if not category or not isinstance(category, dict) or not category.get("table"):
        raise ValueError(f"{visual_type} requires a Category binding.")
    if not y_binding or not isinstance(y_binding, dict) or not y_binding.get("table"):
        raise ValueError(f"{visual_type} requires a Y (value) binding.")

    # Optional legend
    legend_binding = bindings.get("Legend")
    # Optional tooltips (can be list)
    tooltip_bindings = bindings.get("Tooltips") or []
    if isinstance(tooltip_bindings, dict):
        tooltip_bindings = [tooltip_bindings]

    query_state: dict[str, Any] = {
        "Category": {"projections": [_field_projection(category)]},
        "Y": {"projections": [_field_projection(y_binding)]},
    }
    if legend_binding and isinstance(legend_binding, dict) and legend_binding.get("table"):
        query_state["Legend"] = {"projections": [_field_projection(legend_binding)]}

    tooltip_projections = [
        _field_projection(b)
        for b in tooltip_bindings
        if isinstance(b, dict) and b.get("table") and b.get("name")
    ]
    if tooltip_projections:
        query_state["Tooltips"] = {"projections": tooltip_projections}

    default_def = BAR_VISUAL if visual_type == "clusteredBarChart" else COLUMN_VISUAL
    cell_width = context.page_width / context.grid_columns
    x = float(visual.get("x") or 0) * cell_width
    y = float(visual.get("y") or 0) * context.row_height
    width = float(visual.get("w") or default_def.default_width) * cell_width
    height = float(visual.get("h") or default_def.default_height) * context.row_height
    tab_order = float(visual.get("visual_order") or 0)
    artifact_name = _artifact_name(visual, visual_type[:3])

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
            "visualType": visual_type,
            "query": {"queryState": query_state},
            "drillFilterOtherVisuals": True,
        },
    }


def build_bar_visual(visual: dict[str, Any], context: VisualBuildContext) -> dict[str, Any]:
    return _build_bar_like("clusteredBarChart", visual, context)


def build_column_visual(visual: dict[str, Any], context: VisualBuildContext) -> dict[str, Any]:
    return _build_bar_like("clusteredColumnChart", visual, context)


_BAR_SLOTS = (
    VisualSlot(
        name="Category (Y Axis)",
        role="Category",
        field_type="column",
        required=True,
        multi=False,
        description="Category shown on the Y axis.",
    ),
    VisualSlot(
        name="Values (X Axis)",
        role="Y",
        field_type="measure",
        required=True,
        multi=False,
        description="Measure plotted on the X axis.",
    ),
    VisualSlot(
        name="Legend",
        role="Legend",
        field_type="column",
        required=False,
        multi=False,
        description="Optional legend grouping.",
    ),
    VisualSlot(
        name="Tooltips",
        role="Tooltips",
        field_type="any",
        required=False,
        multi=True,
        description="Optional extra fields shown on hover.",
    ),
)

_COLUMN_SLOTS = (
    VisualSlot(
        name="Category (X Axis)",
        role="Category",
        field_type="column",
        required=True,
        multi=False,
        description="Category shown on the X axis.",
    ),
    VisualSlot(
        name="Values (Y Axis)",
        role="Y",
        field_type="measure",
        required=True,
        multi=False,
        description="Measure plotted on the Y axis.",
    ),
    VisualSlot(
        name="Legend",
        role="Legend",
        field_type="column",
        required=False,
        multi=False,
        description="Optional legend grouping.",
    ),
    VisualSlot(
        name="Tooltips",
        role="Tooltips",
        field_type="any",
        required=False,
        multi=True,
        description="Optional extra fields shown on hover.",
    ),
)


BAR_VISUAL = VisualDefinition(
    template_key="clusteredBarChart",
    name="Bar Chart",
    visual_type="clusteredBarChart",
    category="Chart",
    icon="bar_chart",
    description="Compare values across categories with horizontal bars.",
    default_width=4,
    default_height=3,
    slots=_BAR_SLOTS,
    builder=build_bar_visual,
)

COLUMN_VISUAL = VisualDefinition(
    template_key="clusteredColumnChart",
    name="Column Chart",
    visual_type="clusteredColumnChart",
    category="Chart",
    icon="bar_chart_3",
    description="Compare values across categories with vertical columns.",
    default_width=4,
    default_height=3,
    slots=_COLUMN_SLOTS,
    builder=build_column_visual,
)
