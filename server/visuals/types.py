from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class VisualSlot:
    name: str
    role: str
    field_type: str
    required: bool
    multi: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "field_type": self.field_type,
            "required": self.required,
            "multi": self.multi,
            "description": self.description,
        }


@dataclass(frozen=True)
class VisualBuildContext:
    page_width: int
    page_height: int
    grid_columns: int = 12
    row_height: int = 90


VisualBuilder = Callable[[dict[str, Any], VisualBuildContext], dict[str, Any]]


@dataclass(frozen=True)
class VisualDefinition:
    template_key: str
    name: str
    visual_type: str
    category: str
    icon: str
    description: str
    default_width: int
    default_height: int
    slots: tuple[VisualSlot, ...] = field(default_factory=tuple)
    builder: VisualBuilder | None = field(default=None, repr=False, compare=False)

    def to_template_dict(self) -> dict[str, Any]:
        required_slots = [
            {
                "key": slot.role,
                "label": slot.name,
                "kind": slot.field_type,
                "description": slot.description,
            }
            for slot in self.slots
            if slot.required
        ]
        optional_slots = [
            {
                "key": slot.role,
                "label": slot.name,
                "kind": slot.field_type,
                "description": slot.description,
            }
            for slot in self.slots
            if not slot.required
        ]
        return {
            "id": self.template_key,
            "template_key": self.template_key,
            "name": self.name,
            "visual_type": self.visual_type,
            "category": self.category,
            "icon": self.icon,
            "description": self.description,
            "default_width": self.default_width,
            "default_height": self.default_height,
            "slot_definitions": [slot.to_dict() for slot in self.slots],
            "required_slots": required_slots,
            "optional_slots": optional_slots,
            "default_visual_json": {},
        }
