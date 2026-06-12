import React, { useState, useMemo } from 'react';
import { Database, Sigma, X, ChevronDown, ChevronRight, LayoutGrid, Trash2 } from 'lucide-react';
import { getTemplateSlots } from '../Canvas/templateSlots';

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

export default function VisualFieldWell({
  visual,
  template,
  fields,
  onBindingChange,
  onGeometryChange,
  onRemove,
}) {
  const [search, setSearch] = useState('');
  const [collapsedTables, setCollapsedTables] = useState({});

  const slots = useMemo(() => {
    const parsed = getTemplateSlots(template);
    return [...parsed.filter((s) => s.required), ...parsed.filter((s) => !s.required)];
  }, [template]);

  const toggleTable = (tableName) => {
    setCollapsedTables((prev) => ({
      ...prev,
      [tableName]: !prev[tableName],
    }));
  };

  const handleRemoveField = (role, indexToRemove, isMulti) => {
    if (!visual) return;
    const current = visual.bindings?.[role];
    if (isMulti && Array.isArray(current)) {
      const next = current.filter((_, idx) => idx !== indexToRemove);
      onBindingChange(visual.id, role, next.length ? next : null);
    } else {
      onBindingChange(visual.id, role, null);
    }
  };

  const handleDropField = (role, fieldData, isMulti) => {
    if (!visual) return;
    const field = normalizeField(fieldData);
    if (isMulti) {
      const current = visual.bindings?.[role];
      const existing = Array.isArray(current) ? current : current ? [current] : [];
      if (existing.some((b) => b.table === field.table && b.name === field.name)) return;
      onBindingChange(visual.id, role, [...existing, field]);
    } else {
      onBindingChange(visual.id, role, field);
    }
  };

  const handleFieldClick = (fieldData) => {
    if (!visual) return;
    const field = normalizeField(fieldData);

    // Find compatible slots
    const compatibleSlots = slots.filter((slot) => {
      const allowedType = slot.field_type || 'any';
      if (allowedType === 'any') return true;
      if (allowedType === 'measure') return field.kind === 'measure';
      if (allowedType === 'column') return field.kind !== 'measure';
      return true;
    });

    if (!compatibleSlots.length) return;

    // Find first compatible slot that is empty or has room
    const targetSlot = compatibleSlots.find((slot) => {
      const val = visual.bindings?.[slot.role];
      if (slot.multi) {
        return !val || (Array.isArray(val) && val.length === 0);
      }
      return !val;
    }) || compatibleSlots[0];

    handleDropField(targetSlot.role, field, targetSlot.multi);
  };

  // Filter and group fields
  const groupedFields = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = fields.filter((field) => {
      const norm = normalizeField(field);
      return !q || `${norm.table} ${norm.name} ${norm.kind} ${norm.label}`.toLowerCase().includes(q);
    });

    return filtered.reduce((acc, field) => {
      const norm = normalizeField(field);
      if (!acc[norm.table]) {
        acc[norm.table] = [];
      }
      acc[norm.table].push(field);
      return acc;
    }, {});
  }, [fields, search]);

  if (!visual) {
    return (
      <div style={{ color: 'var(--muted)', fontSize: '0.84rem', textAlign: 'center', padding: '24px 0' }}>
        Select a visual on the canvas to configure fields.
      </div>
    );
  }

  return (
    <div className="field-well">
      <div className="field-well__header" style={{ display: 'flex', alignItems: 'center', justifyBetween: 'space-between', gap: 10, paddingBottom: 12, borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <LayoutGrid size={16} style={{ color: 'var(--purple)' }} />
          <div style={{ fontWeight: 700, fontSize: '0.92rem' }}>{visual.name || template?.name}</div>
        </div>
        {onRemove && (
          <button
            type="button"
            className="btn-close"
            onClick={onRemove}
            title="Delete Visual"
            style={{
              marginLeft: 'auto',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--danger)',
              padding: 4,
              borderRadius: 4,
            }}
          >
            <Trash2 size={15} />
          </button>
        )}
      </div>

      {/* Geometry inputs if provided */}
      {onGeometryChange && (
        <div className="field-well__geometry" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, margin: '12px 0' }}>
          {['x', 'y', 'w', 'h'].map((key) => (
            <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <label style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--muted-light)', textTransform: 'uppercase' }}>{key}</label>
              <input
                type="number"
                min={key === 'w' || key === 'h' ? 1 : 0}
                className="form-input"
                style={{ padding: '4px 6px', fontSize: '0.8rem' }}
                value={visual[key] ?? 0}
                onChange={(e) => onGeometryChange(visual.id, { [key]: parseInt(e.target.value) || (key === 'w' || key === 'h' ? 1 : 0) })}
              />
            </div>
          ))}
        </div>
      )}

      {/* Slots List */}
      <div className="field-well__slots" style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
        {slots.map((slot) => {
          const bindingVal = visual.bindings?.[slot.role];
          const isMulti = Boolean(slot.multi);
          const boundFields = isMulti ? (Array.isArray(bindingVal) ? bindingVal : bindingVal ? [bindingVal] : []) : (bindingVal ? [bindingVal] : []);

          return (
            <div
              key={slot.role}
              className="field-slot"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                try {
                  const fieldData = JSON.parse(e.dataTransfer.getData('field'));
                  handleDropField(slot.role, fieldData, isMulti);
                } catch (err) {
                  console.error('Drop error:', err);
                }
              }}
              style={{
                background: 'var(--bg)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: '10px 12px',
                display: 'flex',
                flexDirection: 'column',
                gap: 6
              }}
            >
              <div className="field-slot__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 700 }}>
                  {slot.name}
                  {slot.required && <span style={{ color: 'var(--danger)' }}> *</span>}
                </span>
                <span className="badge badge--purple" style={{ fontSize: '0.62rem', padding: '1px 5px', textTransform: 'uppercase' }}>
                  {slot.field_type || 'any'}
                </span>
              </div>

              {/* Chips or Empty State */}
              <div className="field-slot__chips" style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {boundFields.map((f, index) => {
                  const norm = normalizeField(f);
                  const Icon = norm.kind === 'measure' ? Sigma : Database;
                  return (
                    <div
                      key={`${norm.table}.${norm.name}.${index}`}
                      className="field-chip"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        background: 'var(--surface)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '4px 8px',
                        fontSize: '0.74rem',
                        fontWeight: 600,
                        color: 'var(--text-2)'
                      }}
                    >
                      <Icon size={12} style={{ color: 'var(--purple)', opacity: 0.8 }} />
                      <span>{norm.table}.{norm.name}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveField(slot.role, index, isMulti)}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          cursor: 'pointer',
                          color: 'var(--muted)',
                          padding: 2,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '0.8rem'
                        }}
                      >
                        <X size={11} />
                      </button>
                    </div>
                  );
                })}

                {/* Empty State Target */}
                {(isMulti || boundFields.length === 0) && (
                  <div
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      border: '1px dashed var(--border-strong)',
                      borderRadius: 'var(--radius-sm)',
                      background: 'rgba(255, 255, 255, 0.03)',
                      color: 'var(--muted-light)',
                      fontSize: '0.72rem',
                      textAlign: 'center',
                      cursor: 'default',
                      userSelect: 'none'
                    }}
                  >
                    Drop fields here or click below
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="divider" style={{ margin: '16px 0' }} />

      {/* Collapsible Field Browser */}
      <div className="collapsible-fields">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontWeight: 700, fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--muted-light)' }}>
            Field Browser
          </div>
          <input
            type="search"
            className="form-input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search fields..."
            style={{ padding: '6px 10px', fontSize: '0.8rem' }}
          />

          <div style={{ maxHeight: 240, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4, paddingRight: 4 }}>
            {Object.entries(groupedFields).map(([tableName, tableFields]) => {
              const isCollapsed = collapsedTables[tableName];
              return (
                <div key={tableName} style={{ display: 'flex', flexDirection: 'column' }}>
                  <button
                    type="button"
                    onClick={() => toggleTable(tableName)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      width: '100%',
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      padding: '6px 4px',
                      fontSize: '0.78rem',
                      fontWeight: 700,
                      color: 'var(--text)',
                      textAlign: 'left'
                    }}
                  >
                    {isCollapsed ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
                    <Database size={13} style={{ color: 'var(--muted)' }} />
                    <span>{tableName}</span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--muted-light)', fontWeight: 500, marginLeft: 'auto' }}>
                      ({tableFields.length})
                    </span>
                  </button>

                  {!isCollapsed && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, paddingLeft: 20 }}>
                      {tableFields.map((field, idx) => {
                        const norm = normalizeField(field);
                        const Icon = norm.kind === 'measure' ? Sigma : Database;
                        return (
                          <div
                            key={`${norm.table}.${norm.name}.${idx}`}
                            draggable
                            onDragStart={(e) => e.dataTransfer.setData('field', JSON.stringify(field))}
                            onClick={() => handleFieldClick(field)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 8,
                              padding: '5px 8px',
                              borderRadius: 'var(--radius-sm)',
                              fontSize: '0.76rem',
                              color: 'var(--text-2)',
                              cursor: 'pointer',
                              userSelect: 'none',
                              transition: 'background 0.2s ease',
                            }}
                            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-2)'; }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                          >
                            <Icon size={12} style={{ color: 'var(--muted-light)' }} />
                            <span>{norm.name}</span>
                            <span style={{ fontSize: '0.62rem', fontWeight: 700, marginLeft: 'auto', textTransform: 'uppercase', opacity: 0.6 }}>
                              {norm.kind}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}

            {Object.keys(groupedFields).length === 0 && (
              <div style={{ color: 'var(--muted-light)', fontStyle: 'italic', fontSize: '0.76rem', textAlign: 'center', padding: 12 }}>
                No fields match search
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
