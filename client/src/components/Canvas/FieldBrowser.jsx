import React, { useMemo, useState } from 'react';
import { Database, Sigma } from 'lucide-react';

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
    table: field.table || field.table_name || 'Unknown',
    name,
    kind,
    data_type: field.data_type || field.dataType || null,
    label: field.label || `${field.table || field.table_name || 'Unknown'}.${name}`,
  };
}

export default function FieldBrowser({ fields, onAssignField, selectedVisualId }) {
  const [query, setQuery] = useState('');

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (fields || [])
      .map(normalizeField)
      .filter((field) => {
        if (!q) {
          return true;
        }
        return `${field.table} ${field.name} ${field.kind} ${field.label}`.toLowerCase().includes(q);
      })
      .reduce((acc, field) => {
        if (!acc[field.table]) {
          acc[field.table] = [];
        }
        acc[field.table].push(field);
        return acc;
      }, {});
  }, [fields, query]);

  const fieldCount = useMemo(() => Object.values(grouped).reduce((count, tableFields) => count + tableFields.length, 0), [grouped]);

  return (
    <div className="panel-card">
      <div className="panel-card__title">Field Browser</div>
      <div className="helper-text">
        Browse semantic model columns and click a field to assign it to the selected visual.
      </div>
      <input
        className="input"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search tables or columns"
      />
      <div className="mini-summary">
        <div>{fieldCount} matching fields</div>
        <div>{selectedVisualId ? 'Visual selected' : 'Select a visual first'}</div>
      </div>
      <div className="field-picker__list">
        {Object.entries(grouped).length ? (
          Object.entries(grouped).map(([table, tableFields]) => (
            <div key={table} className="field-picker__group">
              <div className="field-picker__group-title">
                <Database size={14} />
                {table}
              </div>
              <div className="field-picker__group-items">
                {tableFields.map((field) => {
                  const Icon = field.kind === 'measure' ? Sigma : Database;
                  return (
                    <button
                      key={`${field.table}.${field.name}.${field.kind}`}
                      type="button"
                      className="field-picker__item"
                      onClick={() => onAssignField(field)}
                    >
                      <Icon size={16} />
                      <span>{field.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state">No fields matched your search.</div>
        )}
      </div>
    </div>
  );
}
