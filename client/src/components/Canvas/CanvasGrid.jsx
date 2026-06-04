import React, { useMemo } from 'react';
import { WidthProvider } from 'react-grid-layout';
import GridLayout from 'react-grid-layout';
import VisualTile from './VisualTile';

const ResponsiveGridLayout = WidthProvider(GridLayout);

function toNumber(value, fallback) {
  const nextValue = Number(value);
  return Number.isFinite(nextValue) ? nextValue : fallback;
}

function normalizeVisual(visual, template) {
  const defaultWidth = template?.default_width || 3;
  const defaultHeight = template?.default_height || 2;
  return {
    ...visual,
    x: toNumber(visual?.x ?? visual?.grid_position?.col, 0),
    y: toNumber(visual?.y ?? visual?.grid_position?.row, 0),
    w: toNumber(visual?.w ?? visual?.grid_position?.w, defaultWidth),
    h: toNumber(visual?.h ?? visual?.grid_position?.h, defaultHeight),
  };
}

function resolveTemplate(templateMap, templateKey) {
  if (templateKey === null || templateKey === undefined) {
    return null;
  }
  return (
    templateMap.get(templateKey) ||
    templateMap.get(String(templateKey)) ||
    templateMap.get(String(templateKey).toLowerCase()) ||
    templateMap.get(String(templateKey).toUpperCase()) ||
    null
  );
}

export default function CanvasGrid({
  activePage,
  templates,
  onLayoutChange,
  onDropTemplate,
  onSelectVisual,
  onDeleteVisual,
  selectedVisualId,
}) {
  const templateMap = useMemo(() => {
    const map = new Map();
    templates.forEach((template) => {
      const keys = [template.id, String(template.id), template.template_key, template.visual_type]
        .filter(Boolean)
        .flatMap((key) => [key, String(key).toLowerCase(), String(key).toUpperCase()]);
      keys.forEach((key) => map.set(key, template));
    });
    return map;
  }, [templates]);
  const visuals = useMemo(
    () =>
      (activePage?.visuals || []).map((visual) =>
        normalizeVisual(visual, resolveTemplate(templateMap, visual.visual_template_id) || resolveTemplate(templateMap, visual.template_key)),
      ),
    [activePage?.visuals, templateMap],
  );
  const layout = useMemo(
    () =>
      visuals.map((visual) => ({
        i: String(visual.id),
        x: toNumber(visual.x, 0),
        y: toNumber(visual.y, 0),
        w: toNumber(visual.w, 3),
        h: toNumber(visual.h, 2),
      })),
    [visuals],
  );

  return (
    <div className="canvas-stage">
      <div className="canvas-grid">
        {activePage ? (
          <ResponsiveGridLayout
            className="layout"
            cols={12}
            rowHeight={90}
            width={activePage?.width || 1280}
            layout={layout}
            isDroppable
            onLayoutChange={onLayoutChange}
            onDrop={(currentLayout, droppedItem, event) => {
              const templateId = event.dataTransfer.getData('templateId');
              const templateKey =
                event.dataTransfer.getData('application/x-bifoundry-template') ||
                (event.dataTransfer.getData('text/plain') || '').replace(/^template:/, '');
              const nextTemplate = templateId || templateKey;
              if (nextTemplate) {
                onDropTemplate(nextTemplate, toNumber(droppedItem?.x, 0), toNumber(droppedItem?.y, 0));
              }
            }}
            draggableHandle=".visual-drag-handle"
            compactType={null}
            preventCollision={false}
          >
            {visuals.map((visual) => {
              const template = resolveTemplate(templateMap, visual.visual_template_id) || resolveTemplate(templateMap, visual.template_key);
              return (
                <div
                  key={String(visual.id)}
                  data-grid={{
                    x: toNumber(visual.x, 0),
                    y: toNumber(visual.y, 0),
                    w: toNumber(visual.w, 3),
                    h: toNumber(visual.h, 2),
                  }}
                >
                  <VisualTile
                    visual={visual}
                    template={template}
                    selected={selectedVisualId === visual.id}
                    onSelect={() => onSelectVisual(visual.id)}
                    onDelete={() => onDeleteVisual(visual.id)}
                  />
                </div>
              );
            })}
          </ResponsiveGridLayout>
        ) : (
          <div className="empty-state empty-state--canvas">Create a page to start laying out visuals.</div>
        )}
      </div>
    </div>
  );
}
