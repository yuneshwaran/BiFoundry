import React, { useState } from 'react';
import { X } from 'lucide-react';

export default function AddPageModal({ isOpen, onClose, onCreate }) {
  const [name, setName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [width, setWidth] = useState(1280);
  const [height, setHeight] = useState(720);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const cleanName = name.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
    onCreate({
      name: cleanName || `page_${Date.now()}`,
      display_name: displayName.trim() || name.trim() || 'Untitled Page',
      width: Number(width) || 1280,
      height: Number(height) || 720,
    });
    setName('');
    setDisplayName('');
    setWidth(1280);
    setHeight(720);
    onClose();
  };

  return (
    <div className="add-page-modal-overlay">
      <div className="add-page-modal-backdrop" onClick={onClose} />
      <div className="add-page-modal-content card">
        <div className="add-page-modal-header">
          <div className="card-title" style={{ margin: 0 }}>Add New Page</div>
          <button
            className="btn-close"
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--muted)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 4,
              borderRadius: '50%',
              transition: 'background 0.2s ease',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-2)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
          >
            <X size={16} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="form-stack" style={{ marginTop: 16 }}>
          <div className="form-group">
            <label className="form-label">Page Key (system name)</label>
            <input
              className="form-input"
              value={name}
              onChange={(e) => {
                const val = e.target.value;
                setName(val);
                if (!displayName || displayName === val) {
                  setDisplayName(val);
                }
              }}
              placeholder="e.g. sales_summary"
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Display Name</label>
            <input
              className="form-input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. Sales Summary"
              required
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Width (px)</label>
              <input
                className="form-input"
                type="number"
                min="300"
                max="8000"
                value={width}
                onChange={(e) => setWidth(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Height (px)</label>
              <input
                className="form-input"
                type="number"
                min="300"
                max="8000"
                value={height}
                onChange={(e) => setHeight(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="add-page-modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 20 }}>
            <button className="btn btn-ghost" type="button" onClick={onClose}>
              Cancel
            </button>
            <button className="btn btn-primary" type="submit">
              Add Page
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
