from typing import Any

from visuals.bar import BAR_VISUAL, COLUMN_VISUAL
from visuals.pie import PIE_VISUAL
from visuals.slicer import SLICER_VISUAL
from visuals.table import TABLE_VISUAL
from visuals.types import VisualBuildContext, VisualDefinition


_VISUALS: dict[str, VisualDefinition] = {
    TABLE_VISUAL.template_key: TABLE_VISUAL,
    BAR_VISUAL.template_key: BAR_VISUAL,
    COLUMN_VISUAL.template_key: COLUMN_VISUAL,
    PIE_VISUAL.template_key: PIE_VISUAL,
    SLICER_VISUAL.template_key: SLICER_VISUAL,
}


def list_visual_definitions() -> list[dict[str, Any]]:
    return [definition.to_template_dict() for definition in _VISUALS.values()]


def get_visual_definition(template_key: str | None) -> VisualDefinition | None:
    if not template_key:
        return None
    return _VISUALS.get(template_key)


def build_visual(
    template_key: str,
    visual: dict[str, Any],
    context: VisualBuildContext,
) -> dict[str, Any]:
    definition = get_visual_definition(template_key)
    if not definition or not definition.builder:
        raise ValueError(f"Unsupported visual template '{template_key}'.")
    return definition.builder(visual, context)


def validate_visual_bindings(
    definition: VisualDefinition,
    visual: dict[str, Any],
    field_index: dict[str, dict[str, Any]],
) -> list[str]:
    errors = []
    bindings = visual.get("bindings") or {}
    for slot in definition.slots:
        candidate = bindings.get(slot.role)
        if slot.required and not candidate:
            errors.append(f"Missing required binding '{slot.role}'.")
            continue
        if not candidate:
            continue

        values = candidate if isinstance(candidate, list) else [candidate]
        if not slot.multi and len(values) > 1:
            errors.append(f"Binding '{slot.role}' accepts only one field.")
        for value in values:
            if not isinstance(value, dict):
                errors.append(f"Binding '{slot.role}' contains an invalid field.")
                continue
            table = value.get("table") or value.get("tableName")
            name = value.get("name") or value.get("field") or value.get("column")
            field_key = f"{table}.{name}" if table and name else ""
            if not field_key or field_key not in field_index:
                errors.append(
                    f"Bound field '{field_key or value}' was not found in the selected semantic snapshot."
                )
    return errors