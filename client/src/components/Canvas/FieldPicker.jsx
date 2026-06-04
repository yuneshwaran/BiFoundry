import React, { useMemo, useState } from 'react';
import { Database, Sigma, X } from 'lucide-react';

function normalizeField(field) {
  if (typeof field === 'string') {
    const [table = 'Unknown', name = ''] = field.split('.');
    return {
      table,
      name,
      kind: 'column',
      data_type: null,
      label: field,
    };
  }
  const name = field.name || field.field || field.column || '';
  const kind = field.kind || field.field_type || field.type || 'column';
  return {
    table: field.table || field.table_name || '',
    name,
    kind,
    data_type: field.data_type || field.dataType || null,
    label: field.label || `${field.table || field.table_name || 'Unknown'}.${name}`,
  };
}

export default function FieldPicker({ slot, value, fields, onChange }) {
  const [query, setQuery] = useState('');
  const allowedType = slot.field_type || 'any';
  const multi = Boolean(slot.multi);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return fields.filter((field) => {
      const normalized = normalizeField(field);
      const matchesType = allowedType === 'any' || normalized.kind === allowedType;
      const matchesQuery = !q || `${normalized.table} ${normalized.name} ${normalized.kind} ${normalized.label}`.toLowerCase().includes(q);
      return matchesType && matchesQuery;
    });
  }, [allowedType, fields, query]);

  const grouped = useMemo(() => {
    return filtered.reduce((acc, field) => {
      const normalized = normalizeField(field);
      if (!acc[normalized.table]) {
        acc[normalized.table] = [];
      }
      acc[normalized.table].push(field);
      return acc;
    }, {});
  }, [filtered]);

  const selected = multi ? value || [] : value ? [value] : [];

  const isSelected = (candidate) =>
    selected.some((item) => {
      const normalized = normalizeField(item);
      return normalized.table === candidate.table && normalized.name === candidate.name && normalized.kind === candidate.kind;
    });

  return (
    <div className="slot-picker">
      <div className="slot-picker__header">
        <span>
          {slot.name}
          {slot.required ? <span className="slot-picker__required"> *</span> : null}
        </span>
        <span className="slot-picker__kind">{allowedType}</span>
      </div>
      <input className="input" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search fields" />
      <div className="field-picker__list">
        {Object.entries(grouped).map(([table, tableFields]) => (
          <div key={table} className="field-picker__group">
            <div className="field-picker__group-title">
              <Database size={14} />
              {table}
            </div>
            <div className="field-picker__group-items">
              {tableFields.map((field) => {
                const normalized = normalizeField(field);
                const active = isSelected(normalized);
                const Icon = normalized.kind === 'measure' ? Sigma : Database;
                return (
                  <button
                    key={`${normalized.table}.${normalized.name}.${normalized.kind}`}
                    type="button"
                    className={`field-picker__item ${active ? 'field-picker__item--active' : ''}`}
                    onClick={() => {
                      if (multi) {
                        if (active) {
                          return;
                        }
                        onChange([...selected, normalized]);
                        return;
                      }
                      onChange(normalized);
                    }}
                  >
                    <Icon size={16} />
                    <span>{normalized.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      {selected.length ? (
        <button type="button" className="mini-button" onClick={() => onChange(multi ? [] : null)}>
          <X size={14} />
          Clear
        </button>
      ) : null}
    </div>
  );
}
