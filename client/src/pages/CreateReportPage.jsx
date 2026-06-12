import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  BarChart2,
  BarChart3,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Database,
  FileStack,
  Filter,
  Layers,
  LayoutTemplate,
  Loader2,
  PieChart,
  Plus,
  Server,
  Table2,
  Wifi,
  WifiOff,
  X,
  Zap,
} from 'lucide-react';
import { usePowerBi } from '../context/PowerBiContext';
import {
  listWorkspaces,
  listSemanticModels,
  createProject,
  selectSemanticModel,
  listProjectVisualTemplates,
} from '../services/projectApi';
import FieldBrowser from '../components/Canvas/FieldBrowser';
import VisualFieldWell from '../components/ProjectPage/VisualFieldWell';
import { getTemplateSlots } from '../components/Canvas/templateSlots';

const MOCK_TEMPLATES = [
  { id: 1, name: 'Sales Dashboard',  color: 'purple', pages: 3 },
  { id: 2, name: 'HR Overview',      color: 'teal',   pages: 2 },
  { id: 3, name: 'Finance Report',   color: 'blue',   pages: 4 },
  { id: 4, name: 'Executive Summary',color: 'pink',   pages: 2 },
];

// ─── Step Indicator ──────────────────────────────────────────────────────────

const STEPS = [
  { num: 1, label: 'Choose Connection' },
  { num: 2, label: 'Semantic Model' },
  { num: 3, label: 'Starting Point' },
  { num: 4, label: 'Canvas & Fields' },
];

function StepIndicator({ current }) {
  return (
    <div className="step-indicator">
      {STEPS.map((step, idx) => {
        const done   = step.num < current;
        const active = step.num === current;
        return (
          <React.Fragment key={step.num}>
            {idx > 0 && (
              <div
                style={{
                  height: 2, flex: 1,
                  background: done ? 'var(--purple)' : 'var(--border)',
                  transition: 'background 0.3s ease',
                  margin: '0 6px',
                }}
              />
            )}
            <div className="step-item" style={{ flexShrink: 0 }}>
              <div className={`step-circle${active ? ' step-circle--active' : done ? ' step-circle--done' : ''}`}>
                {done ? <Check size={13} /> : step.num}
              </div>
              <span
                className={`step-label${active ? ' step-label--active' : done ? ' step-label--done' : ''}`}
                style={{ display: window.innerWidth < 700 ? 'none' : undefined }}
              >
                {step.label}
              </span>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Step 1: Choose Connection ───────────────────────────────────────────────

function Step1({ connections, selectedId, onSelect }) {
  if (connections.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state__icon"><Server size={24} /></div>
        <div className="empty-state__title">No connections available</div>
        <div className="empty-state__body">
          Go to the Connections page to create an Azure AD profile first.
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="section-label">Select a Connection to use for this report</div>
      <div className="cards-grid">
        {connections.map((conn) => {
          const isAuth     = conn?.session?.is_authenticated;
          const isSelected = conn.id === selectedId;
          return (
            <div
              key={conn.id}
              className={`conn-card${isSelected ? ' conn-card--selected' : ''}`}
              onClick={() => onSelect(conn.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(conn.id); } }}
            >
              <div className="conn-card__top">
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div className="conn-card__icon"><Server size={18} /></div>
                  <div>
                    <div className="conn-card__title">{conn.label}</div>
                    <div className="conn-card__meta">{conn.tenant_id || 'No tenant'}</div>
                  </div>
                </div>
                {isSelected ? (
                  <div style={{ width: 26, height: 26, borderRadius: '50%', background: 'var(--purple)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
                    <Check size={14} />
                  </div>
                ) : null}
              </div>
              <div className="conn-card__kv">
                <div className="conn-card__kv-item">
                  <div className="conn-card__kv-label">Status</div>
                  <div className="conn-card__kv-value" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    {isAuth ? (
                      <><Wifi size={11} style={{ color: 'var(--teal)' }} /> Connected</>
                    ) : (
                      <><WifiOff size={11} style={{ color: 'var(--muted)' }} /> Offline</>
                    )}
                  </div>
                </div>
                <div className="conn-card__kv-item">
                  <div className="conn-card__kv-label">Workspace</div>
                  <div className="conn-card__kv-value">
                    {conn.active_workspace_name || conn.active_workspace_id || '—'}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Step 2: Semantic Model (real API) ───────────────────────────────────────

function Step2({
  connectionId,
  workspaceId,
  onWorkspaceChange,
  workspaces,
  loadingWorkspaces,
  workspaceError,
  models,
  loadingModels,
  modelsError,
  selectedModelId,
  onSelectModel,
}) {
  return (
    <div>
      {/* Workspace selector */}
      <div style={{ marginBottom: 20 }}>
        <div className="section-label">Workspace</div>
        {loadingWorkspaces ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--muted)', padding: '12px 0' }}>
            <Loader2 size={16} style={{ animation: 'spin 0.7s linear infinite' }} /> Loading workspaces…
          </div>
        ) : workspaceError ? (
          <div className="status-banner status-banner--error" style={{ marginBottom: 12 }}>
            {workspaceError}
          </div>
        ) : (
          <select
            className="form-input form-select"
            value={workspaceId}
            onChange={(e) => onWorkspaceChange(e.target.value)}
            style={{ maxWidth: 360 }}
          >
            <option value="">Select a workspace</option>
            {workspaces.map((ws) => (
              <option key={ws.workspace_id || ws.id} value={ws.workspace_id || ws.id}>{ws.name}</option>
            ))}
          </select>
        )}
      </div>

      {/* Semantic models */}
      <div className="section-label">Semantic Models in this Workspace</div>
      {!workspaceId ? (
        <div className="empty-state">
          <div className="empty-state__icon"><Database size={22} /></div>
          <div className="empty-state__title">Select a workspace first</div>
        </div>
      ) : loadingModels ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '24px 0', color: 'var(--muted)' }}>
          <Loader2 size={18} style={{ animation: 'spin 0.7s linear infinite' }} /> Loading models…
        </div>
      ) : modelsError ? (
        <div className="status-banner status-banner--error">{modelsError}</div>
      ) : models.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon"><Database size={22} /></div>
          <div className="empty-state__title">No semantic models found</div>
          <div className="empty-state__body">This workspace has no published semantic models.</div>
        </div>
      ) : (
        <div className="cards-grid">
          {models.map((model) => {
            const isSelected = model.id === selectedModelId;
            return (
              <div
                key={model.id}
                className={`card card--hover${isSelected ? ' card--selected' : ''}`}
                style={{ padding: 18, cursor: 'pointer' }}
                onClick={() => onSelectModel(model.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter') onSelectModel(model.id); }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <div style={{ width: 38, height: 38, borderRadius: 10, background: 'linear-gradient(135deg, #0d9488, #14b8a6)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
                    <Database size={18} />
                  </div>
                  {isSelected && (
                    <div style={{ width: 24, height: 24, borderRadius: '50%', background: 'var(--purple)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
                      <Check size={13} />
                    </div>
                  )}
                </div>
                <div style={{ fontWeight: 700, marginBottom: 4 }}>{model.name}</div>
                {model.configuredBy && (
                  <div style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>
                    By: {model.configuredBy}
                  </div>
                )}
                {model.isRefreshable !== undefined && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: 4 }}>
                    {model.isRefreshable ? '↻ Refreshable' : 'Static'}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Step 3: Starting Point ──────────────────────────────────────────────────

function Step3({ choice, onChoice, selectedTemplate, onSelectTemplate }) {
  return (
    <div>
      <div className="section-label">How do you want to start?</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        {/* From Template */}
        <div
          style={{
            border: `2px solid ${choice === 'template' ? 'var(--purple)' : 'var(--border)'}`,
            borderRadius: 'var(--radius-lg)',
            padding: 20,
            cursor: 'pointer',
            background: choice === 'template' ? 'var(--purple-light)' : 'var(--surface)',
            boxShadow: choice === 'template' ? '0 0 0 3px rgba(124,58,237,0.1)' : 'none',
            transition: 'all 0.18s ease',
          }}
          onClick={() => onChoice('template')}
          role="button" tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') onChoice('template'); }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'linear-gradient(135deg,#7c3aed,#9f5de8)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
              <LayoutTemplate size={20} />
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '0.95rem' }}>Start from Template</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>Pre-built page layout</div>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {MOCK_TEMPLATES.map((tpl) => (
              <div
                key={tpl.id}
                style={{
                  padding: '10px 12px',
                  borderRadius: 'var(--radius)',
                  border: `1px solid ${selectedTemplate === tpl.id ? 'var(--purple)' : 'var(--border)'}`,
                  background: selectedTemplate === tpl.id ? 'rgba(124,58,237,0.1)' : 'var(--surface)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
                onClick={(e) => { e.stopPropagation(); onChoice('template'); onSelectTemplate(tpl.id); }}
                role="button" tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter') { onChoice('template'); onSelectTemplate(tpl.id); } }}
              >
                <div
                  style={{
                    height: 32, borderRadius: 6, marginBottom: 8,
                    background: tpl.color === 'purple' ? 'linear-gradient(135deg,#7c3aed,#9f5de8)'
                      : tpl.color === 'teal'   ? 'linear-gradient(135deg,#0d9488,#14b8a6)'
                      : tpl.color === 'blue'   ? 'linear-gradient(135deg,#2563eb,#60a5fa)'
                      : 'linear-gradient(135deg,#ec4899,#f472b6)',
                  }}
                />
                <div style={{ fontSize: '0.75rem', fontWeight: 700 }}>{tpl.name}</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--muted)', marginTop: 2 }}>{tpl.pages} pages</div>
              </div>
            ))}
          </div>
        </div>

        {/* Blank canvas */}
        <div
          style={{
            border: `2px dashed ${choice === 'blank' ? 'var(--purple)' : 'var(--border-strong)'}`,
            borderRadius: 'var(--radius-lg)',
            padding: 20,
            cursor: 'pointer',
            background: choice === 'blank' ? 'var(--purple-light)' : 'var(--surface)',
            boxShadow: choice === 'blank' ? '0 0 0 3px rgba(124,58,237,0.1)' : 'none',
            transition: 'all 0.18s ease',
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            minHeight: 280, gap: 14, textAlign: 'center',
          }}
          onClick={() => onChoice('blank')}
          role="button" tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') onChoice('blank'); }}
        >
          <div style={{
            width: 56, height: 56, borderRadius: 'var(--radius-md)',
            background: choice === 'blank' ? 'linear-gradient(135deg,#7c3aed,#9f5de8)' : 'var(--bg-2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: choice === 'blank' ? '#fff' : 'var(--muted)',
            transition: 'all 0.18s ease',
          }}>
            <Plus size={28} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1rem', marginBottom: 4 }}>Blank Canvas</div>
            <div style={{ fontSize: '0.82rem', color: 'var(--muted)', lineHeight: 1.5 }}>
              Start from scratch and design every page yourself using the visual palette.
            </div>
          </div>
          {choice === 'blank' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--purple)', fontWeight: 700, fontSize: '0.82rem' }}>
              <Check size={15} /> Selected
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Step 4: Canvas & Field Mapping ─────────────────────────────────────────

const ICONS = {
  tableEx: Table2,
  clusteredBarChart: BarChart3,
  clusteredColumnChart: BarChart2,
  donutChart: PieChart,
  slicer: Filter,
};

function VisualBlock({ visual, isSelected, onClick, onRemove, visualTemplates }) {
  const template = visualTemplates.find((t) => t.template_key === visual.type);
  const VIcon = ICONS[visual.type] || BarChart3;
  return (
    <div
      className={`canvas-visual-block${isSelected ? ' canvas-visual-block--selected' : ''}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      style={{ position: 'relative' }}
      onKeyDown={(e) => { if (e.key === 'Enter') onClick(); }}
    >
      <div className="canvas-visual-block__title">{template?.name || visual.type}</div>
      <div className="canvas-visual-block__preview">
        <VIcon size={36} style={{ opacity: 0.2 }} />
      </div>
      <button
        type="button"
        style={{
          position: 'absolute', top: 6, right: 6,
          background: 'var(--danger-light)', border: 'none', borderRadius: 6,
          width: 22, height: 22, display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', color: 'var(--danger)', opacity: 0,
          transition: 'opacity 0.15s ease',
        }}
        className="visual-remove-btn"
        onClick={(e) => { e.stopPropagation(); onRemove(); }}
      >
        <X size={12} />
      </button>
      <style>{`.canvas-visual-block:hover .visual-remove-btn { opacity: 1 !important; }`}</style>
    </div>
  );
}

function Step4({
  pages,
  activePage,
  onAddPage,
  onSelectPage,
  visuals,
  onAddVisual,
  onRemoveVisual,
  selectedVisual,
  onSelectVisual,
  onAssignField,
  fields,
  visualTemplates,
  handleUpdatePage,
  handleUpdateVisual,
  handleBindingChange,
}) {
  const [isPageConfigOpen, setIsPageConfigOpen] = useState(true);

  const handleDragStart = (e, visualType) => {
    e.dataTransfer.setData('visualType', visualType);
  };
  const handleDropOnCanvas = (e) => {
    e.preventDefault();
    const type = e.dataTransfer.getData('visualType');
    if (type) onAddVisual(type);
  };

  const activePageObj = pages.find((p) => p.id === activePage) || pages[0];
  const sel = visuals.find((v) => v.id === selectedVisual);

  const templateMap = React.useMemo(() => {
    const map = new Map();
    visualTemplates.forEach((template) => {
      const keys = [template.id, String(template.id), template.template_key, template.visual_type]
        .filter(Boolean)
        .flatMap((key) => [key, String(key).toLowerCase()]);
      keys.forEach((key) => map.set(key, template));
    });
    return map;
  }, [visualTemplates]);

  const selectedTemplate = sel
    ? templateMap.get(sel.type) ||
      templateMap.get(String(sel.type || '').toLowerCase())
    : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="canvas-toolbar">
        <div style={{ display: 'flex', gap: 8, flex: 1, flexWrap: 'wrap' }}>
          {pages.map((pg) => (
            <button
              key={pg.id}
              type="button"
              className={`canvas-page-tab${pg.id === activePage ? ' canvas-page-tab--active' : ''}`}
              onClick={() => onSelectPage(pg.id)}
            >
              {pg.name}
            </button>
          ))}
          <button type="button" className="canvas-page-tab" onClick={onAddPage} style={{ borderStyle: 'dashed' }}>
            <Plus size={12} /> Add Page
          </button>
        </div>
      </div>

      <div className="canvas-layout">
        <div className="canvas-palette">
          <div className="section-label">Visual Palette</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8, marginBottom: 16 }}>
            {visualTemplates.map((vt) => {
              const Icon = ICONS[vt.visual_type] || ICONS[vt.template_key] || BarChart2;
              return (
                <div
                  key={vt.template_key}
                  className="palette-visual-card"
                  draggable
                  onDragStart={(e) => handleDragStart(e, vt.template_key)}
                  onClick={() => onAddVisual(vt.template_key)}
                  title={`Drag to canvas or click to add ${vt.name}`}
                  style={{
                    cursor: 'pointer',
                    padding: '10px 8px',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius)',
                    background: 'var(--surface)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    textAlign: 'center',
                    gap: 6
                  }}
                >
                  <div className="palette-visual-card__icon" style={{ color: 'var(--purple)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Icon size={18} />
                  </div>
                  <div>
                    <div className="palette-visual-card__name" style={{ fontSize: '0.75rem', fontWeight: 600 }}>{vt.name}</div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="divider" />
          <div className="section-label">Field Browser</div>
          {fields.length === 0 ? (
            <div style={{ color: 'var(--muted)', fontSize: '0.8rem', padding: '12px 6px', fontStyle: 'italic' }}>
              No fields available. Select a semantic model first.
            </div>
          ) : (
            <FieldBrowser
              fields={fields}
              onAssignField={(f) => {
                if (!selectedVisual || !onAssignField) return;
                const normalized = { table: f.table, name: f.name, kind: f.kind, label: f.label };
                onAssignField(selectedVisual, normalized);
              }}
              selectedVisualId={selectedVisual}
            />
          )}
        </div>

        <div className="canvas-area">
          <div
            className="canvas-drop-zone"
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDropOnCanvas}
          >
            {visuals.length === 0 ? (
              <div className="canvas-drop-zone--empty">
                <Layers size={40} style={{ opacity: 0.18 }} />
                <div style={{ fontWeight: 700 }}>Drop visuals here</div>
                <div style={{ fontSize: '0.8rem' }}>Drag from the Visual Palette or click a visual type to add it</div>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, alignContent: 'start' }}>
                {visuals.map((v) => (
                  <div key={v.id} style={{ height: 160 }}>
                    <VisualBlock
                      visual={v}
                      isSelected={v.id === selectedVisual}
                      onClick={() => onSelectVisual(v.id === selectedVisual ? null : v.id)}
                      onRemove={() => onRemoveVisual(v.id)}
                      visualTemplates={visualTemplates}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="canvas-properties">
          {!sel ? (
            <div className="form-stack">
              <div 
                className="section-label" 
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                  cursor: 'pointer',
                  userSelect: 'none'
                }}
                onClick={() => setIsPageConfigOpen(!isPageConfigOpen)}
              >
                <span>Page Configuration</span>
                {isPageConfigOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </div>
              {isPageConfigOpen && (
                <>
                  <div className="form-group">
                    <label className="form-label">Page Name</label>
                    <input
                      className="form-input"
                      value={activePageObj?.name || ''}
                      onChange={(e) => handleUpdatePage(activePage, { name: e.target.value, display_name: e.target.value })}
                      placeholder="Page name"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Canvas Width (px)</label>
                    <input
                      className="form-input"
                      type="number"
                      value={activePageObj?.width || 1280}
                      onChange={(e) => handleUpdatePage(activePage, { width: parseInt(e.target.value) || 1280 })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Canvas Height (px)</label>
                    <input
                      className="form-input"
                      type="number"
                      value={activePageObj?.height || 720}
                      onChange={(e) => handleUpdatePage(activePage, { height: parseInt(e.target.value) || 720 })}
                    />
                  </div>
                </>
              )}
            </div>
          ) : (
            <VisualFieldWell
              visual={sel}
              template={selectedTemplate}
              fields={fields}
              onBindingChange={handleBindingChange}
              onGeometryChange={handleUpdateVisual}
              onRemove={() => onRemoveVisual(sel.id)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

const buildFieldsFromTables = (tables) => {
  const catalog = [];
  for (const table of (tables || [])) {
    const tableName = table.name || table.tableName || table.displayName || 'Table';
    for (const column of (table.columns || [])) {
      const kind = column.kind || column.type || 'column';
      catalog.push({
        table: tableName,
        name: column.name || column.columnName,
        kind: kind.toLowerCase() === 'measure' ? 'measure' : 'column',
        data_type: column.dataType || column.type,
        label: `${tableName}.${column.name || column.columnName}`,
      });
    }
    for (const measure of (table.measures || [])) {
      catalog.push({
        table: tableName,
        name: measure.name,
        kind: 'measure',
        data_type: measure.dataType || 'measure',
        label: `${tableName}.${measure.name}`,
      });
    }
  }
  return catalog;
};

// ─── Main Wizard ─────────────────────────────────────────────────────────────

export default function CreateReportPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { connections, activeConnectionId } = usePowerBi();

  const [step, setStep] = useState(1);

  // Step 1
  const [selectedConnectionId, setSelectedConnectionId] = useState(null);

  // Step 2 — real Power BI data
  const [workspaceId,      setWorkspaceId]      = useState('');
  const [workspaces,       setWorkspaces]        = useState([]);
  const [loadingWorkspaces,setLoadingWorkspaces] = useState(false);
  const [workspaceError,   setWorkspaceError]    = useState('');
  const [models,           setModels]            = useState([]);
  const [loadingModels,    setLoadingModels]     = useState(false);
  const [modelsError,      setModelsError]       = useState('');
  const [selectedModelId,  setSelectedModelId]   = useState('');
  const [selectedModelName,setSelectedModelName] = useState('');

  // Loaded metadata fields and templates
  const [fields,           setFields]            = useState([]);
  const [loadingFields,    setLoadingFields]     = useState(false);
  const [fieldsError,      setFieldsError]       = useState('');
  const [visualTemplates,  setVisualTemplates]   = useState([]);

  // Step 3
  const [startChoice,       setStartChoice]       = useState('');
  const [selectedTemplate,  setSelectedTemplate]  = useState(null);

  // Step 4
  const [pages,         setPages]         = useState([{ id: 'p1', name: 'Page 1', width: 1280, height: 720, visuals: [] }]);
  const [activePage,    setActivePage]    = useState('p1');
  const [selectedVisual,setSelectedVisual]= useState(null);

  const activePageObj = pages.find((p) => p.id === activePage) || pages[0];
  const visuals = activePageObj?.visuals || [];

  const handleUpdatePage = useCallback((pageId, updates) => {
    setPages((prev) => prev.map((page) => (page.id === pageId ? { ...page, ...updates } : page)));
  }, []);

  // Submission state
  const [submitting,  setSubmitting]  = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [created,     setCreated]     = useState(null); // { projectId, reportName }

  // Load visual templates on mount
  useEffect(() => {
    listProjectVisualTemplates()
      .then((data) => {
        setVisualTemplates(data || []);
      })
      .catch((err) => console.error('Failed to load visual templates:', err));
  }, []);

  // Pre-select active connection
  useEffect(() => {
    if (!selectedConnectionId && activeConnectionId) {
      setSelectedConnectionId(activeConnectionId);
    }
  }, [activeConnectionId, selectedConnectionId]);

  // Pre-fill from template navigation
  useEffect(() => {
    if (location.state?.templateId) {
      setStartChoice('template');
      setSelectedTemplate(location.state.templateId);
      setStep(3);
    }
  }, [location.state]);

  // Load workspaces when entering step 2 and a connection is selected
  useEffect(() => {
    if (step !== 2 || !selectedConnectionId) return;
    setWorkspaceError('');
    setLoadingWorkspaces(true);
    listWorkspaces(selectedConnectionId)
      .then((data) => {
        // API may return { value: [...] } or an array
        const list = Array.isArray(data) ? data : (data?.value || []);
        setWorkspaces(list);
      })
      .catch((err) => setWorkspaceError(err.message || 'Failed to load workspaces.'))
      .finally(() => setLoadingWorkspaces(false));
  }, [step, selectedConnectionId]);

  // Load semantic models when workspace changes
  useEffect(() => {
    if (!workspaceId || !selectedConnectionId) { setModels([]); return; }
    setModelsError('');
    setLoadingModels(true);
    setSelectedModelId('');
    setSelectedModelName('');
    listSemanticModels(selectedConnectionId, workspaceId)
      .then((data) => {
        const list = Array.isArray(data) ? data : (data?.value || []);
        setModels(list);
      })
      .catch((err) => setModelsError(err.message || 'Failed to load semantic models.'))
      .finally(() => setLoadingModels(false));
  }, [workspaceId, selectedConnectionId]);

  const canNext = () => {
    if (step === 1) return !!selectedConnectionId;
    if (step === 2) return !!selectedModelId;
    if (step === 3) return !!startChoice && (startChoice === 'blank' || !!selectedTemplate);
    return true;
  };

  const handleNext = () => {
    if (canNext() && step < 4) setStep((s) => s + 1);
  };

  const handleBack = () => {
    if (step > 1) setStep((s) => s - 1);
  };

  const handleSelectModel = async (id) => {
    setSelectedModelId(id);
    const found = models.find((m) => m.id === id);
    setSelectedModelName(found?.name || id);

    setFieldsError('');
    setLoadingFields(true);
    try {
      const res = await selectSemanticModel(selectedConnectionId, workspaceId, id);
      const tables = res?.raw?.tables || [];
      const catalog = buildFieldsFromTables(tables);
      setFields(catalog);
    } catch (err) {
      console.error('Failed to load semantic model metadata:', err);
      setFieldsError(err.message || 'Failed to select semantic model metadata.');
    } finally {
      setLoadingFields(false);
    }
  };

  const handleAddPage = () => {
    const newId   = `p${Date.now()}`;
    const newName = `Page ${pages.length + 1}`;
    setPages((prev) => [...prev, { id: newId, name: newName, display_name: newName, width: 1280, height: 720, visuals: [] }]);
    setActivePage(newId);
  };

  const handleAddVisual = useCallback((type) => {
    const newVisual = {
      id: `v-${Date.now()}`,
      type,
      name: `${type} Visual`,
      x: 0,
      y: 0,
      w: 4,
      h: 3,
      bindings: {},
    };
    setPages((prev) =>
      prev.map((p) =>
        p.id === activePage
          ? { ...p, visuals: [...(p.visuals || []), newVisual] }
          : p
      )
    );
    setSelectedVisual(newVisual.id);
  }, [activePage]);

  const handleRemoveVisual = useCallback((id) => {
    setPages((prev) =>
      prev.map((p) =>
        p.id === activePage
          ? { ...p, visuals: (p.visuals || []).filter((v) => v.id !== id) }
          : p
      )
    );
    setSelectedVisual((prev) => (prev === id ? null : prev));
  }, [activePage]);

  const handleUpdateVisual = useCallback((visualId, updates) => {
    setPages((prev) =>
      prev.map((p) =>
        p.id === activePage
          ? {
              ...p,
              visuals: (p.visuals || []).map((v) =>
                v.id === visualId ? { ...v, ...updates } : v
              ),
            }
          : p
      )
    );
  }, [activePage]);

  const handleAssignField = (visualId, field) => {
    setPages((prev) =>
      prev.map((p) =>
        p.id === activePage
          ? {
              ...p,
              visuals: (p.visuals || []).map((v) => {
                if (v.id !== visualId) return v;
                const curr = { ...(v.bindings || {}) };
                const type = v.type || 'tableEx';

                const template = visualTemplates.find((t) => t.template_key === type);
                const slots = getTemplateSlots(template).filter((slot) => {
                  const allowedType = slot.field_type || 'any';
                  if (allowedType === 'any') return true;
                  if (allowedType === 'measure') return field.kind === 'measure';
                  if (allowedType === 'column') return field.kind !== 'measure';
                  return true;
                });

                const target = slots.find((slot) => !curr[slot.role] || (slot.multi && (!Array.isArray(curr[slot.role]) || curr[slot.role].length === 0))) || slots[0] || { role: 'Values', multi: true };

                if (target.multi) {
                  const existing = Array.isArray(curr[target.role]) ? curr[target.role] : curr[target.role] ? [curr[target.role]] : [];
                  if (!existing.some((b) => b.table === field.table && b.name === field.name)) {
                    curr[target.role] = [...existing, field];
                  }
                } else {
                  curr[target.role] = field;
                }
                return { ...v, bindings: curr };
              }),
            }
          : p
      )
    );
  };

  const handleBindingChange = useCallback((visualId, slotRole, nextValue) => {
    setPages((prev) =>
      prev.map((p) =>
        p.id === activePage
          ? {
              ...p,
              visuals: (p.visuals || []).map((v) =>
                v.id === visualId
                  ? {
                      ...v,
                      bindings: {
                        ...(v.bindings || {}),
                        [slotRole]: nextValue,
                      },
                    }
                  : v
              ),
            }
          : p
      )
    );
  }, [activePage]);

  // ── Final submit: create project + report ──────────────────────────────────
  const handleFinish = async () => {
    setSubmitError('');
    setSubmitting(true);
    try {
      const reportName = selectedModelName
        ? `${selectedModelName} Report`
        : 'New Report';

      const payload = {
        name: reportName,
        source_workspace_id: workspaceId,
        source_semantic_model_id: selectedModelId,
        source_semantic_model_name: selectedModelName,
        powerbi_connection_id: selectedConnectionId,
        pages: pages.map((pg, idx) => ({
          name: pg.name.toLowerCase().replace(/\s+/g, '_'),
          display_name: pg.name,
          width: pg.width || 1280,
          height: pg.height || 720,
          page_order: idx,
          visuals: (pg.visuals || []).map((v, vi) => ({
            template_key: v.type,
            name: v.name || `${v.type} ${vi + 1}`,
            x: v.x || 0,
            y: v.y || 0,
            w: v.w || 4,
            h: v.h || 3,
            bindings: v.bindings || {},
            config: v.config || {},
            raw: {},
          })),
          raw: {},
        })),
        raw: {},
      };

      const result = await createProject(payload);
      setCreated({ projectId: result.id, reportName });
    } catch (err) {
      setSubmitError(err.message || 'Failed to create project.');
    } finally {
      setSubmitting(false);
    }
  };

  const selectedConn = connections.find((c) => c.id === selectedConnectionId);

  // ── Success screen ─────────────────────────────────────────────────────────
  if (created) {
    return (
      <div className="page-content" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '80vh' }}>
        <div className="card" style={{ maxWidth: 480, width: '100%', padding: 40, textAlign: 'center' }}>
          <div style={{ width: 72, height: 72, borderRadius: '50%', background: 'var(--success-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px', color: 'var(--success)' }}>
            <Check size={36} />
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 8 }}>Project created!</h2>
          <p style={{ color: 'var(--muted)', marginBottom: 28, lineHeight: 1.6 }}>
            <strong>{created.reportName}</strong> has been created successfully. You can now open it in the project editor to add visuals and compile your PBIP package.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button className="btn btn-ghost" type="button" onClick={() => navigate('/projects')}>
              View all projects
            </button>
            <button className="btn btn-primary" type="button" onClick={() => navigate(`/projects/${created.projectId}`)}>
              Open in editor <ChevronRight size={15} />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {/* Page Header */}
      <div className="page-hero">
        <div>
          <div className="page-hero__eyebrow">
            <FileStack size={12} />
            Report Wizard
          </div>
          <h1 className="page-hero__title">Create Report</h1>
          <p className="page-hero__subtitle">
            Follow the steps to connect, choose a semantic model, and design your report pages.
          </p>
        </div>
        <div className="page-hero__chips">
          {selectedConn && <div className="hero-chip"><Server size={12} />{selectedConn.label}</div>}
          {selectedModelName && <div className="hero-chip"><Database size={12} />{selectedModelName}</div>}
        </div>
      </div>

      {/* Error banner */}
      {submitError && (
        <div className="status-banner status-banner--error">
          <span>{submitError}</span>
          <button className="status-banner__close" onClick={() => setSubmitError('')} type="button"><X size={14} /></button>
        </div>
      )}

      {/* Step indicator */}
      <div className="wizard-header">
        <StepIndicator current={step} />
      </div>

      {/* Step content */}
      <div>
        {step === 1 && (
          <Step1
            connections={connections}
            selectedId={selectedConnectionId}
            onSelect={setSelectedConnectionId}
          />
        )}
        {step === 2 && (
          <Step2
            connectionId={selectedConnectionId}
            workspaceId={workspaceId}
            onWorkspaceChange={setWorkspaceId}
            workspaces={workspaces}
            loadingWorkspaces={loadingWorkspaces}
            workspaceError={workspaceError}
            models={models}
            loadingModels={loadingModels}
            modelsError={modelsError}
            selectedModelId={selectedModelId}
            onSelectModel={handleSelectModel}
          />
        )}
        {step === 3 && (
          <Step3
            choice={startChoice}
            onChoice={setStartChoice}
            selectedTemplate={selectedTemplate}
            onSelectTemplate={setSelectedTemplate}
          />
        )}
        {step === 4 && (
          <Step4
            pages={pages}
            activePage={activePage}
            onAddPage={handleAddPage}
            onSelectPage={setActivePage}
            visuals={visuals}
            onAddVisual={handleAddVisual}
            onRemoveVisual={handleRemoveVisual}
            selectedVisual={selectedVisual}
            onSelectVisual={setSelectedVisual}
            onAssignField={handleAssignField}
            fields={fields}
            visualTemplates={visualTemplates}
            handleUpdatePage={handleUpdatePage}
            handleUpdateVisual={handleUpdateVisual}
            handleBindingChange={handleBindingChange}
          />
        )}
      </div>

      {/* Footer nav */}
      <div className="wizard-footer">
        <button
          className="btn btn-ghost"
          type="button"
          onClick={step === 1 ? () => navigate('/projects') : handleBack}
        >
          <ChevronLeft size={16} />
          {step === 1 ? 'Cancel' : 'Back'}
        </button>

        <div style={{ display: 'flex', gap: 8 }}>
          {step < 4 ? (
            <button
              className="btn btn-primary"
              type="button"
              onClick={handleNext}
              disabled={!canNext()}
            >
              Next Step <ChevronRight size={16} />
            </button>
          ) : (
            <button
              className="btn btn-primary"
              type="button"
              onClick={handleFinish}
              disabled={submitting}
            >
              {submitting ? (
                <><Loader2 size={15} style={{ animation: 'spin 0.7s linear infinite' }} /> Creating…</>
              ) : (
                <><Zap size={15} /> Create Project &amp; Report</>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
