function buildSlot(name, role, fieldType, required, multi, description = '') {
  return {
    name,
    role,
    field_type: fieldType,
    required,
    multi,
    description,
  };
}

function normalizeSlot(slot, required) {
  const role = slot.role || slot.key || slot.name;
  const fieldType = slot.field_type || (String(slot.kind || '').includes('measure') ? 'measure' : String(slot.kind || '').includes('column') ? 'column' : 'any');
  return buildSlot(
    slot.name || slot.label || role,
    role,
    fieldType,
    required,
    Boolean(slot.multi || String(slot.kind || '').includes('list')),
    slot.description || '',
  );
}

export function getTemplateSlots(template) {
  const slotDefinitions = template?.slot_definitions;
  if (Array.isArray(slotDefinitions) && slotDefinitions.length) {
    return slotDefinitions;
  }

  const requiredSlots = (template?.required_slots || []).map((slot) => normalizeSlot(slot, true));
  const optionalSlots = (template?.optional_slots || []).map((slot) => normalizeSlot(slot, false));
  return [...requiredSlots, ...optionalSlots];
}
