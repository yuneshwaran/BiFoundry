import React, { useRef, useState } from 'react';
import {
  BarChart3,
  Calendar,
  Download,
  Eye,
  FileArchive,
  FileStack,
  Layers,
  LayoutTemplate,
  PieChart,
  Plus,
  Table2,
  Trash2,
  Upload,
  X,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const TEMPLATE_COLORS = ['purple', 'teal', 'pink', 'blue', 'amber', 'indigo'];

const MOCK_TEMPLATES = [
  {
    id: 1,
    name: 'Sales Performance Dashboard',
    category: 'Finance',
    visualCount: 8,
    importDate: '2026-05-14',
    color: 'purple',
    icon: BarChart3,
    description: 'KPI tiles, trend lines, and regional breakdown for sales data.',
  },
  {
    id: 2,
    name: 'HR Analytics Overview',
    category: 'HR',
    visualCount: 6,
    importDate: '2026-05-20',
    color: 'teal',
    icon: PieChart,
    description: 'Headcount, attrition, and department distribution charts.',
  },
  {
    id: 3,
    name: 'Inventory Tracker',
    category: 'Operations',
    visualCount: 5,
    importDate: '2026-06-01',
    color: 'blue',
    icon: Table2,
    description: 'Stock levels, reorder alerts, and supplier summary tables.',
  },
  {
    id: 4,
    name: 'Executive Summary',
    category: 'Management',
    visualCount: 4,
    importDate: '2026-06-05',
    color: 'pink',
    icon: Layers,
    description: 'High-level KPIs and scorecards for leadership review.',
  },
  {
    id: 5,
    name: 'Marketing Campaign Report',
    category: 'Marketing',
    visualCount: 7,
    importDate: '2026-06-08',
    color: 'amber',
    icon: BarChart3,
    description: 'Conversion funnels, channel breakdown, and ROI tracking.',
  },
  {
    id: 6,
    name: 'Financial Statements',
    category: 'Finance',
    visualCount: 9,
    importDate: '2026-06-10',
    color: 'indigo',
    icon: FileStack,
    description: 'P&L, balance sheet, and cash flow waterfall charts.',
  },
];

const CATEGORIES = ['All', 'Finance', 'HR', 'Operations', 'Management', 'Marketing'];

export default function TemplatesPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [templates, setTemplates] = useState(MOCK_TEMPLATES);
  const [activeCategory, setActiveCategory] = useState('All');
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadNotice, setUploadNotice] = useState('');
  const [previewTemplate, setPreviewTemplate] = useState(null);

  const filtered = activeCategory === 'All'
    ? templates
    : templates.filter((t) => t.category === activeCategory);

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFileUpload(file);
  };

  const handleFileUpload = (file) => {
    if (!file.name.endsWith('.zip')) {
      setUploadNotice('error:Only .zip PBIP files are supported.');
      return;
    }
    setUploading(true);
    setUploadNotice('');
    setTimeout(() => {
      const newTemplate = {
        id: Date.now(),
        name: file.name.replace('.zip', '').replace(/_/g, ' '),
        category: 'Imported',
        visualCount: Math.floor(Math.random() * 8) + 2,
        importDate: new Date().toISOString().split('T')[0],
        color: TEMPLATE_COLORS[templates.length % TEMPLATE_COLORS.length],
        icon: BarChart3,
        description: 'Imported from PBIP package.',
      };
      setTemplates((prev) => [newTemplate, ...prev]);
      setUploading(false);
      setUploadNotice(`success:Imported "${newTemplate.name}" successfully.`);
    }, 1200);
  };

  const handleDelete = (id) => {
    setTemplates((prev) => prev.filter((t) => t.id !== id));
  };

  const noticeType = uploadNotice.startsWith('error:') ? 'error' : 'success';
  const noticeText = uploadNotice.replace(/^(error|success):/, '');

  return (
    <div className="page-content">
      {/* Hero */}
      <div className="page-hero">
        <div>
          <div className="page-hero__eyebrow">
            <LayoutTemplate size={12} />
            Report Blueprints
          </div>
          <h1 className="page-hero__title">Report Templates</h1>
          <p className="page-hero__subtitle">
            Browse and import PBIP report templates. Start a new project from a pre-built
            layout or upload your own packaged template.
          </p>
        </div>
        <div className="page-hero__chips">
          <div className="hero-chip">
            <Layers size={12} />
            {templates.length} template{templates.length !== 1 ? 's' : ''}
          </div>
          <button
            className="btn btn-ghost"
            style={{ background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.18)', color: '#fff' }}
            type="button"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload size={15} />
            Import from PBIP
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            style={{ display: 'none' }}
            onChange={(e) => { if (e.target.files?.[0]) handleFileUpload(e.target.files[0]); }}
          />
        </div>
      </div>

      {/* Banners */}
      {uploadNotice && (
        <div className={`status-banner status-banner--${noticeType}`}>
          <span>{noticeText}</span>
          <button className="status-banner__close" onClick={() => setUploadNotice('')} type="button">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Category filter */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setActiveCategory(cat)}
            style={{
              padding: '6px 16px',
              borderRadius: 'var(--radius-full)',
              border: '1px solid',
              borderColor: activeCategory === cat ? 'var(--purple)' : 'var(--border-strong)',
              background: activeCategory === cat ? 'var(--purple)' : 'var(--surface)',
              color: activeCategory === cat ? '#fff' : 'var(--text-2)',
              fontFamily: 'inherit',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Templates grid + upload zone */}
      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="section-label">
            {activeCategory === 'All' ? 'All Templates' : activeCategory} &mdash; {filtered.length} found
          </div>
          <div className="cards-grid">
            {filtered.map((tpl) => {
              const Icon = tpl.icon;
              return (
                <div key={tpl.id} className="template-card">
                  <div className={`template-card__header template-card__header--${tpl.color}`}>
                    <div className="template-card__preview-icon">
                      <Icon size={26} />
                    </div>
                  </div>
                  <div className="template-card__body">
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
                      <div className="template-card__name">{tpl.name}</div>
                      <span className={`badge badge--${tpl.color === 'purple' ? 'purple' : tpl.color === 'teal' ? 'teal' : tpl.color === 'pink' ? 'pink' : tpl.color === 'blue' ? 'blue' : tpl.color === 'amber' ? 'amber' : 'purple'}`}>
                        {tpl.category}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted)', lineHeight: 1.5 }}>
                      {tpl.description}
                    </div>
                    <div className="template-card__meta">
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Layers size={11} /> {tpl.visualCount} visuals
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Calendar size={11} /> {tpl.importDate}
                      </span>
                    </div>
                    <div className="template-card__actions">
                      <button
                        className="btn btn-ghost btn-sm"
                        type="button"
                        onClick={() => setPreviewTemplate(tpl)}
                      >
                        <Eye size={13} /> Preview
                      </button>
                      <button
                        className="btn btn-primary btn-sm"
                        type="button"
                        onClick={() => navigate('/create', { state: { templateId: tpl.id } })}
                      >
                        <Plus size={13} /> Use in Report
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        type="button"
                        style={{ marginLeft: 'auto' }}
                        onClick={() => handleDelete(tpl.id)}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Upload zone sidebar */}
        <div style={{ width: 280, flexShrink: 0 }} className="sticky-panel">
          <div className="section-label">Import Template</div>
          <div
            className={`upload-zone${isDragOver ? ' upload-zone--drag-over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="upload-zone__icon">
              {uploading ? (
                <div className="spinner" />
              ) : (
                <FileArchive size={24} />
              )}
            </div>
            <div className="upload-zone__title">
              {uploading ? 'Importing...' : 'Drop PBIP here'}
            </div>
            <div className="upload-zone__body">
              {uploading
                ? 'Processing your template package...'
                : 'Drag & drop a .zip PBIP file, or click to browse'}
            </div>
            {!uploading && (
              <button
                className="btn btn-primary btn-sm"
                type="button"
                onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
              >
                <Upload size={13} /> Choose File
              </button>
            )}
          </div>

          <div className="section-label" style={{ marginTop: 20 }}>About Templates</div>
          <div className="panel-card">
            <div className="panel-card__title">PBIP Format</div>
            <div className="panel-card__body">
              <p style={{ marginBottom: 10 }}>
                Templates are Power BI Project (PBIP) packages exported as <code>.zip</code>
                archives. They contain pre-built page layouts and visual configurations.
              </p>
              <p>
                After importing, use <strong>Use in Report</strong> to start a new project
                with the template's page structure.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Preview slide-in panel */}
      {previewTemplate && (
        <div className="panel-overlay panel-overlay--active">
          <div className="panel-backdrop" onClick={() => setPreviewTemplate(null)} />
          <div className="slide-panel">
            <div className="slide-panel__header">
              <div className="slide-panel__title">Template Preview</div>
              <button
                className="btn btn-icon btn-ghost"
                type="button"
                onClick={() => setPreviewTemplate(null)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="slide-panel__body">
              {/* Preview header */}
              <div
                className={`template-card__header template-card__header--${previewTemplate.color}`}
                style={{ borderRadius: 'var(--radius-md)', marginBottom: 20, minHeight: 140 }}
              >
                <div className="template-card__preview-icon" style={{ width: 60, height: 60 }}>
                  <previewTemplate.icon size={30} />
                </div>
              </div>

              <div style={{ marginBottom: 8 }}>
                <span className={`badge badge--${previewTemplate.color === 'purple' ? 'purple' : previewTemplate.color === 'teal' ? 'teal' : previewTemplate.color === 'pink' ? 'pink' : 'blue'}`}>
                  {previewTemplate.category}
                </span>
              </div>
              <h2 style={{ fontWeight: 800, fontSize: '1.1rem', marginBottom: 8 }}>{previewTemplate.name}</h2>
              <p style={{ fontSize: '0.87rem', color: 'var(--muted)', lineHeight: 1.6, marginBottom: 20 }}>
                {previewTemplate.description}
              </p>

              <div className="panel-card__kv">
                {[
                  { label: 'Visuals', value: `${previewTemplate.visualCount} visual blocks` },
                  { label: 'Category', value: previewTemplate.category },
                  { label: 'Imported', value: previewTemplate.importDate },
                ].map((r) => (
                  <div key={r.label} className="panel-card__kv-row">
                    <div className="panel-card__kv-label">{r.label}</div>
                    <div className="panel-card__kv-value">{r.value}</div>
                  </div>
                ))}
              </div>

              {/* Mock page thumbnail previews */}
              <div style={{ marginTop: 20 }}>
                <div className="section-label">Pages in Template</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  {Array.from({ length: Math.min(previewTemplate.visualCount, 4) }).map((_, i) => (
                    <div
                      key={i}
                      style={{
                        height: 80,
                        borderRadius: 'var(--radius)',
                        background: 'var(--bg)',
                        border: '1px solid var(--border)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.72rem',
                        color: 'var(--muted)',
                        fontWeight: 600,
                      }}
                    >
                      Page {i + 1}
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="slide-panel__footer">
              <button
                className="btn btn-primary"
                type="button"
                style={{ flex: 1 }}
                onClick={() => { setPreviewTemplate(null); navigate('/create', { state: { templateId: previewTemplate.id } }); }}
              >
                <Plus size={15} />
                Use in Report
              </button>
              <button
                className="btn btn-ghost"
                type="button"
                onClick={() => setPreviewTemplate(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
