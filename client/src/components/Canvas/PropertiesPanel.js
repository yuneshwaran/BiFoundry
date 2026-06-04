import React, { useMemo } from 'react';
import FieldPicker from './FieldPicker';
import { getTemplateSlots } from './templateSlots';

export default function PropertiesPanel({
  report,
  selectedVisual,
  templates,
  fields,
  onUpdateReport,
  onUpdateVisual,
  onDeleteVisual,
  onCompile,
  compiling,
  mode = 'builder',
}) {
  const templateMap = useMemo(() => {
    const map = new Map();
    templates.forEach((template) => {
      const keys = [template.id, String(template.id), template.template_key, template.visual_type]
        .filter(Boolean)
        .flatMap((key) => [key, String(key).toLowerCase()]);
      keys.forEach((key) => map.set(key, template));
    });
    return map;
  }, [templates]);

  const selectedTemplate = selectedVisual
    ? templateMap.get(selectedVisual.visual_template_id) ||
      templateMap.get(selectedVisual.template_key) ||
      templateMap.get(String(selectedVisual.template_key || '').toLowerCase()) ||
      templateMap.get(String(selectedVisual.visual_template_id || '').toLowerCase())
    : null;
  const slots = getTemplateSlots(selectedTemplate);
  const visualX = Number.isFinite(Number(selectedVisual?.x)) ? Number(selectedVisual.x) : 0;
  const visualY = Number.isFinite(Number(selectedVisual?.y)) ? Number(selectedVisual.y) : 0;
  const visualW = Number.isFinite(Number(selectedVisual?.w)) ? Number(selectedVisual.w) : 3;
  const visualH = Number.isFinite(Number(selectedVisual?.h)) ? Number(selectedVisual.h) : 2;

  const handleBindingChange = (slot, nextValue) => {
    onUpdateVisual(selectedVisual.id, {
      bindings: {
        ...(selectedVisual.bindings || {}),
        [slot.role]: nextValue,
      },
    });
  };

  const renderBuilder = () => (
    <div className="stack">
      {!selectedVisual ? (
        <div className="panel-card">
          <div className="panel-card__title">Report Focus</div>
          <div className="helper-text">Choose a visual on the canvas to edit its bindings.</div>
          <div className="mini-summary">
            <div>{report?.name}</div>
            <div>{report?.pages?.length || 0} pages</div>
            <div>{report?.settings?.theme_name || 'BIFoundryTheme'}</div>
          </div>
        </div>
      ) : (
        <div className="stack">
          <div className="panel-card">
            <div className="panel-card__title">{selectedTemplate?.name || selectedVisual.template_key}</div>
            <label className="field-label">Visual name</label>
            <input
              className="input"
              type="text"
              value={selectedVisual.name || ''}
              onChange={(event) => onUpdateVisual(selectedVisual.id, { name: event.target.value, visual_name: event.target.value })}
            />
            <div className="grid grid--2">
              <div>
                <label className="field-label">X</label>
                <input className="input" type="number" min="0" value={visualX} onChange={(event) => onUpdateVisual(selectedVisual.id, { x: Number(event.target.value) })} />
              </div>
              <div>
                <label className="field-label">Y</label>
                <input className="input" type="number" min="0" value={visualY} onChange={(event) => onUpdateVisual(selectedVisual.id, { y: Number(event.target.value) })} />
              </div>
              <div>
                <label className="field-label">W</label>
                <input className="input" type="number" min="1" value={visualW} onChange={(event) => onUpdateVisual(selectedVisual.id, { w: Number(event.target.value) })} />
              </div>
              <div>
                <label className="field-label">H</label>
                <input className="input" type="number" min="1" value={visualH} onChange={(event) => onUpdateVisual(selectedVisual.id, { h: Number(event.target.value) })} />
              </div>
            </div>
            <button className="button button--danger" type="button" onClick={() => onDeleteVisual(selectedVisual.id)}>
              Delete Visual
            </button>
          </div>

          <div className="panel-card">
            <div className="panel-card__title">Field Slots</div>
          {slots.length ? (
            slots.map((slot) => (
              <FieldPicker
                key={slot.role}
                slot={slot}
                value={selectedVisual.bindings?.[slot.role]}
                fields={fields}
                onChange={(nextValue) => handleBindingChange(slot, nextValue)}
              />
            ))
            ) : (
              <div className="empty-state">This visual has no configurable slots.</div>
            )}
          </div>
        </div>
      )}

      <div className="panel-card">
        <div className="panel-card__title">Compile</div>
        <button className="button button--primary" type="button" onClick={onCompile} disabled={compiling || !report?.pages?.length}>
          {compiling ? 'Compiling...' : 'Compile PBIP'}
        </button>
        <div className="helper-text">The compiler packages the canvas into a PBIP zip using the connected datasource metadata and template library.</div>
      </div>
    </div>
  );

  const renderSettings = () => (
    <div className="stack">
      <div className="panel-card">
        <div className="panel-card__title">Report Settings</div>
        <label className="field-label">Report name</label>
        <input className="input" type="text" value={report?.name || ''} onChange={(event) => onUpdateReport({ name: event.target.value })} />
        <label className="field-label">Width</label>
        <input
          className="input"
          type="number"
          value={report?.settings?.canvas_width || 1280}
          onChange={(event) => onUpdateReport({ settings: { canvas_width: Number(event.target.value) } })}
        />
        <label className="field-label">Height</label>
        <input
          className="input"
          type="number"
          value={report?.settings?.canvas_height || 720}
          onChange={(event) => onUpdateReport({ settings: { canvas_height: Number(event.target.value) } })}
        />
        <label className="field-label">Theme name</label>
        <input
          className="input"
          type="text"
          value={report?.settings?.theme_name || 'BIFoundryTheme'}
          onChange={(event) => onUpdateReport({ settings: { theme_name: event.target.value } })}
        />
        <label className="field-label">Theme color</label>
        <input
          className="input"
          type="color"
          value={report?.settings?.theme_color || '#154360'}
          onChange={(event) => onUpdateReport({ settings: { theme_color: event.target.value } })}
        />
      </div>
    </div>
  );

  return (
    <aside className="properties-panel">
      <div className="section-title">{mode === 'settings' ? 'Settings' : 'Properties'}</div>
      {mode === 'settings' ? renderSettings() : renderBuilder()}
    </aside>
  );
}
