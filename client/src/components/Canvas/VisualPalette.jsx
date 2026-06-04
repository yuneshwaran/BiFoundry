import React from 'react';
import { ChartBar, ChartColumn, LineChart, PieChart, Table, Columns3, SlidersHorizontal, SquareAsterisk, Hash, Grid2X2 } from 'lucide-react';

const ICONS = {
  clusteredBarChart: ChartBar,
  clusteredColumnChart: ChartColumn,
  lineChart: LineChart,
  areaChart: LineChart,
  card: SquareAsterisk,
  multiRowCard: Columns3,
  tableEx: Table,
  matrix: Grid2X2,
  donutChart: PieChart,
  slicer: SlidersHorizontal,
};

export default function VisualPalette({ templates, onDragStart }) {
  if (!templates.length) {
    return (
      <div className="palette">
        <div className="section-title">Visual Palette</div>
        <div className="empty-state empty-state--canvas">
          No visual templates are available yet. Start the backend so the built-in templates can seed, or import a PBIP report from the Reports page to populate the library.
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
