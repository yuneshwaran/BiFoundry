import React, { useState } from 'react';

export default function PageTabs({ pages, activePageId, onAddPage, onSelectPage, onRenamePage, onMovePage, onDeletePage }) {
  const [editingPageId, setEditingPageId] = useState(null);
  const [draftName, setDraftName] = useState('');

  return (
    <div className="page-tabs">
      {pages.map((page, index) => {
        const isActive = page.id === activePageId;
        const isEditing = editingPageId === page.id;
        return (
          <div key={page.id} className={`page-pill ${isActive ? 'page-pill--active' : ''}`}>
            {isEditing ? (
              <input
                className="input page-pill__input"
                value={draftName}
                autoFocus
                onChange={(event) => setDraftName(event.target.value)}
                onBlur={async () => {
                  setEditingPageId(null);
                  await onRenamePage(page.id, draftName);
                }}
                onKeyDown={async (event) => {
                  if (event.key === 'Enter') {
                    event.currentTarget.blur();
                  }
                  if (event.key === 'Escape') {
                    setEditingPageId(null);
                  }
                }}
              />
            ) : (
              <button
                className="page-pill__button"
                type="button"
                onClick={() => onSelectPage(page.id)}
                onDoubleClick={() => {
                  setDraftName(page.display_name || page.name || '');
                  setEditingPageId(page.id);
                }}
              >
                {page.display_name || page.name}
              </button>
            )}
            <div className="page-pill__controls">
              <button className="mini-button" type="button" onClick={() => onMovePage(page.id, -1)} disabled={index === 0}>
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
        );
      })}
      <button className="mini-button page-tabs__add" type="button" onClick={onAddPage}>
        +
      </button>
    </div>
  );
}
