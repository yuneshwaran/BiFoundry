import React from 'react';
import { getTemplateSlots } from './templateSlots';

function formatBinding(binding) {
  if (!binding) {
    return 'Unbound';
  }
  if (Array.isArray(binding)) {
    if (!binding.length) {
      return 'Unbound';
    }
    return binding.map((item) => formatBinding(item)).join(', ');
  }
  if (typeof binding === 'string') {
    return binding;
  }
  const table = binding.table || binding.table_name || '';
  const field = binding.name || binding.field || binding.column || '';
  const label = binding.label || binding.display_name;
  if (label) {
    return label;
  }
  return table && field ? `${table}.${field}` : field || table || 'Unbound';
}

export default function VisualTile({ visual, template, selected, onSelect, onDelete }) {
  const slots = getTemplateSlots(template);
  return (
    <div className={`visual-card ${selected ? 'visual-card--selected' : ''}`} onClick={onSelect} role="button" tabIndex={0}>
      <div className="visual-card__header visual-drag-handle">
        <div>
          <div className="visual-card__type">{template?.name || template?.visual_type || visual.template_key}</div>
          <div className="visual-card__name">{visual.name || visual.visual_name}</div>
        </div>
        <button className="mini-button mini-button--danger visual-card__delete" type="button" onClick={(event) => {
          event.stopPropagation();
          onDelete();
        }}>
          ×
        </button>
      </div>
      <div className="visual-card__body">
        {slots.length ? (
          slots.map((slot) => (
            <div key={slot.role} className="visual-card__binding">
              <strong>{slot.role}:</strong> {formatBinding(visual.bindings?.[slot.role])}
            </div>
          ))
        ) : (
          <div className="visual-card__binding">No slots configured.</div>
        )}
      </div>
    </div>
  );
}
