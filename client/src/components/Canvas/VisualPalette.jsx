import React from 'react';
import { Hash, Table } from 'lucide-react';

const ICONS = {
  tableEx: Table,
};

export default function VisualPalette({ templates, onDragStart }) {
  if (!templates.length) {
    return (
      <div className="palette">
        <div className="section-title">Visual Palette</div>
        <div className="empty-state empty-state--canvas">
          No code-first visual definitions are available.
        </div>
      </div>
    );
  }

  return (
    <div className="palette">
      <div className="section-title">Visual Palette</div>
      <div className="palette__grid">
        {templates.map((template) => {
          const Icon = ICONS[template.visual_type] || Hash;
          return (
            <div
              key={template.id}
              className="palette-card"
              draggable
              onDragStart={(event) => onDragStart(event, template)}
            >
              <div className="palette-card__icon">
                <Icon size={18} />
              </div>
              <div className="palette-card__title">{template.name}</div>
              <div className="palette-card__meta">{template.description}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
