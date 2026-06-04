import React, { useEffect, useRef, useState } from 'react';

const GRID_COLUMNS = 12;
const ROW_HEIGHT = 72;

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function fieldSummary(bindings) {
  const entries = Object.entries(bindings || {});
  if (!entries.length) {
    return 'No field bindings yet.';
  }
  return entries
    .map(([slot, value]) => {
      if (Array.isArray(value)) {
        return `${slot}: ${value.map((item) => item.label || item.name).join(', ')}`;
      }
      return `${slot}: ${value?.label || value?.name || value}`;
    })
    .join(' | ');
}

export default function CanvasEditor({
  report,
  activePageId,
  selectedVisualId,
  onSelectPage,
  onAddPage,
  onRenamePage,
  onDeletePage,
  onMovePage,
  onSelectVisual,
  onAddVisual,
  onMoveVisual,
  onResizeVisual,
}) {
  const canvasRef = useRef(null);
  const resizeRef = useRef(null);
  const [activePageDraftName, setActivePageDraftName] = useState('');

  const pages = report?.pages || [];
  const activePage = pages.find((page) => page.id === activePageId) || pages[0] || null;
  useEffect(() => {
    setActivePageDraftName(activePage?.display_name || activePage?.name || '');
  }, [activePage?.id, activePage?.display_name, activePage?.name]);

  useEffect(() => {
    const onPointerMove = (event) => {
      if (!resizeRef.current) {
        return;
      }

      const canvasEl = canvasRef.current;
      if (!canvasEl) {
        return;
      }

      const rect = canvasEl.getBoundingClientRect();
      const cellWidth = rect.width / GRID_COLUMNS;
      const { startX, startY, original, visualId } = resizeRef.current;
      const deltaX = event.clientX - startX;
      const deltaY = event.clientY - startY;
      const nextWidth = clamp(Math.round(original.w + deltaX / cellWidth), 1, GRID_COLUMNS - original.x);
      const nextHeight = clamp(Math.round(original.h + deltaY / ROW_HEIGHT), 1, 20);
      onResizeVisual(visualId, { w: nextWidth, h: nextHeight });
    };

    const onPointerUp = () => {
      resizeRef.current = null;
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    };

    if (resizeRef.current) {
      window.addEventListener('pointermove', onPointerMove);
      window.addEventListener('pointerup', onPointerUp);
    }

    return () => {
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    };
  }, [onResizeVisual, activePageId, activePage?.id]);

  const handleDrop = (event) => {
    event.preventDefault();
    const canvasEl = canvasRef.current;
    if (!canvasEl || !activePage) {
      return;
    }

    const rect = canvasEl.getBoundingClientRect();
    const cellWidth = rect.width / GRID_COLUMNS;
    const x = clamp(Math.floor((event.clientX - rect.left) / cellWidth), 0, GRID_COLUMNS - 1);
    const y = clamp(Math.floor((event.clientY - rect.top) / ROW_HEIGHT), 0, 40);
    const dataText = event.dataTransfer.getData('text/plain') || '';
    const templateKey =
      event.dataTransfer.getData('application/x-bifoundry-template') ||
      (dataText.startsWith('template:') ? dataText.slice('template:'.length) : '');
    const visualId =
      event.dataTransfer.getData('application/x-bifoundry-visual-id') ||
      (dataText.startsWith('visual:') ? dataText.slice('visual:'.length) : '');

    if (templateKey) {
      onAddVisual(templateKey, activePage.id, { x, y });
      return;
    }

    if (visualId) {
      onMoveVisual(Number(visualId), activePage.id, { x, y });
    }
  };

  const currentPageVisuals = activePage?.visuals || [];

  return (
    <section className="canvas-shell">
      <div className="canvas-shell__header">
        <div>
          <div className="section-title">Canvas Builder</div>
          <div className="canvas-shell__subtitle">
            Centered report canvas with Power BI-style page management and drag-to-place visuals.
          </div>
        </div>
        <div className="canvas-shell__actions">
          <button className="button" onClick={onAddPage} type="button">
            Add Page
          </button>
        </div>
      </div>

      {activePage ? (
        <div className="canvas-shell__active-page">
          <label className="field-label">Active page name</label>
          <input
            className="input"
            type="text"
            value={activePageDraftName}
            onChange={(event) => {
              const nextValue = event.target.value;
              setActivePageDraftName(nextValue);
              onRenamePage(activePage.id, nextValue);
            }}
          />
        </div>
      ) : null}

      <div className="canvas-shell__pages">
        {pages.map((page, index) => (
          <div
            key={page.id}
            className={`page-pill ${page.id === activePageId ? 'page-pill--active' : ''}`}
          >
            <button className="page-pill__button" type="button" onClick={() => onSelectPage(page.id)}>
              {page.display_name || page.name}
            </button>
            <div className="page-pill__controls">
              <button
                className="mini-button"
                type="button"
                onClick={() => onMovePage(page.id, -1)}
                disabled={index === 0}
              >
                Up
              </button>
              <button
                className="mini-button"
                type="button"
                onClick={() => onMovePage(page.id, 1)}
                disabled={index === pages.length - 1}
              >
                Down
              </button>
              <button
                className="mini-button mini-button--danger"
                type="button"
                onClick={() => onDeletePage(page.id)}
                disabled={pages.length === 1}
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="canvas-stage">
      <div
          ref={canvasRef}
          className="canvas-grid"
          onDragOver={(event) => event.preventDefault()}
          onDrop={handleDrop}
          style={{
            gridTemplateColumns: `repeat(${GRID_COLUMNS}, minmax(0, 1fr))`,
          }}
        >
          {activePage ? (
            <>
              {currentPageVisuals.length ? (
                currentPageVisuals.map((visual) => {
                  return (
                    <div
                      key={visual.id}
                      className={`visual-card ${selectedVisualId === visual.id ? 'visual-card--selected' : ''}`}
                      style={{
                        gridColumn: `${visual.x + 1} / span ${visual.w}`,
                        gridRow: `${visual.y + 1} / span ${visual.h}`,
                      }}
                      draggable
                      onDragStart={(event) => {
                        event.dataTransfer.setData('application/x-bifoundry-visual-id', String(visual.id));
                        event.dataTransfer.setData('text/plain', `visual:${visual.id}`);
                        event.dataTransfer.effectAllowed = 'copyMove';
                      }}
                      onClick={() => onSelectVisual(visual.id)}
                      role="button"
                      tabIndex={0}
                    >
                      <div className="visual-card__header">
                        <div>
                          <div className="visual-card__type">{visual.template_key}</div>
                          <div className="visual-card__name">{visual.name}</div>
                        </div>
                        <div className="visual-card__badge">{visual.template_key}</div>
                      </div>
                      <div className="visual-card__body">{fieldSummary(visual.bindings)}</div>
                      <div
                        className="visual-card__resize-handle"
                        onPointerDown={(event) => {
                          event.stopPropagation();
                          resizeRef.current = {
                            visualId: visual.id,
                            startX: event.clientX,
                            startY: event.clientY,
                            original: {
                              x: visual.x,
                              y: visual.y,
                              w: visual.w,
                              h: visual.h,
                            },
                          };
                        }}
                      />
                    </div>
                  );
                })
              ) : (
                <div className="canvas-grid__prompt">
                  <div className="canvas-grid__prompt-title">Drop a template here</div>
                  <div className="canvas-grid__prompt-body">
                    Pick a visual from the template panel on the left and drop it into the canvas to
                    start laying out the report.
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state empty-state--canvas">
              Create a canvas report to start laying out visuals.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
