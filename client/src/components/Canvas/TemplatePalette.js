import React from 'react';

export default function TemplatePalette({ templates }) {
  return (
    <div className="palette">
      <div className="section-title">Visual Palette</div>
      <div className="palette__grid">
        {templates.map((template) => (
          <div
            key={template.template_key}
            className="palette-card"
            draggable
            onDragStart={(event) => {
              event.dataTransfer.setData('application/x-bifoundry-template', template.template_key);
              event.dataTransfer.setData('text/plain', `template:${template.template_key}`);
              event.dataTransfer.effectAllowed = 'copyMove';
            }}
          >
            <div className="palette-card__icon">{template.icon || 'visual'}</div>
            <div className="palette-card__title">{template.name}</div>
            <div className="palette-card__meta">{template.description}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
