import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  BarChart3,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Database,
  Download,
  FileStack,
  Filter,
  Layers,
  Loader2,
  PieChart,
  Plus,
  RefreshCw,
  ShieldCheck,
  Table2,
  Trash2,
  X,
  Zap,
} from 'lucide-react';
import {
  compileProject,
  createProjectPage,
  createProjectVisual,
  deleteProjectPage,
  deleteProjectVisual,
  downloadBlob,
  getProject,
  getProjectFields,
  refreshProjectMetadata,
  updateProjectPage,
  validateProject,
  listProjectVisualTemplates,
  updateProjectVisual,
} from '../services/projectApi';
import FieldBrowser from '../components/Canvas/FieldBrowser';
import { getTemplateSlots } from '../components/Canvas/templateSlots';

const VISUAL_TYPES = [
  { key: 'bar-chart',    label: 'Bar Chart',    Icon: BarChart3 },
  { key: 'column-chart', label: 'Column Chart', Icon: BarChart3 },
  { key: 'table',        label: 'Table',        Icon: Table2 },
  { key: 'pie-chart',   label: 'Pie / Donut',  Icon: PieChart },
  { key: 'slicer',      label: 'Slicer',       Icon: Filter },
];

const blankVisual = {
  template_key: 'bar-chart',
  name: 'Visual 1',
  x: 0,
  y: 0,
  w: 4,
  h: 3,
  bindings: '{}',
  config: '{}',
};

export default function ProjectPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const numericProjectId = Number(projectId);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [selectedPageId, setSelectedPageId] = useState(null);
  const [cachedFields, setCachedFields] = useState({ tables: [], fields: [], relationships: [], debug: {} });
  const [pageForm, setPageForm] = useState({ name: '', display_name: '', width: 1280, height: 720 });
  const [visualForm, setVisualForm] = useState(blankVisual);
  const [fieldSearch, setFieldSearch] = useState('');
  const [expandedTables, setExpandedTables] = useState({});
  const [selectedVisualId, setSelectedVisualId] = useState(null);
  const [templates, setTemplates] = useState([]);

  const projectQuery = useQuery({
    queryKey: ['project', numericProjectId],
    queryFn: () => getProject(numericProjectId),
    enabled: Number.isFinite(numericProjectId),
  });

  const fieldsQuery = useQuery({
    queryKey: ['project-fields', numericProjectId],
    queryFn: () => getProjectFields(numericProjectId),
    enabled: Number.isFinite(numericProjectId),
  });

  const templatesQuery = useQuery({
    queryKey: ['project-visual-templates'],
    queryFn: listProjectVisualTemplates,
  });

  useEffect(() => {
    if (templatesQuery.data) setTemplates(templatesQuery.data || []);
  }, [templatesQuery.data]);

  useEffect(() => {
    if (fieldsQuery.data && Array.isArray(fieldsQuery.data.fields) && fieldsQuery.data.fields.length) {
      setCachedFields(fieldsQuery.data);
    }
  }, [fieldsQuery.data]);

  const project = projectQuery.data;
  const pages = useMemo(() => project?.pages || [], [project?.pages]);
  const selectedPage = useMemo(
    () => pages.find((page) => page.id === selectedPageId) || pages[0] || null,
    [pages, selectedPageId],
  );

  useEffect(() => {
    if (pages.length && !selectedPageId) setSelectedPageId(pages[0].id);
  }, [pages, selectedPageId]);

  useEffect(() => {
    if (selectedPage) {
      setPageForm({
        name: selectedPage.page_name || selectedPage.name || '',
        display_name: selectedPage.display_name || selectedPage.name || '',
        width: selectedPage.width || 1280,
        height: selectedPage.height || 720,
      });
    }
  }, [selectedPage]);

  /* ── Mutations ─────────────────────────────────────────────── */

  const refreshMutation = useMutation({
    mutationFn: () => refreshProjectMetadata(numericProjectId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['project', numericProjectId] });
      await queryClient.invalidateQueries({ queryKey: ['project-fields', numericProjectId] });
      setNotice('Metadata refreshed successfully.');
    },
    onError: (e) => setError(e.message || 'Failed to refresh metadata.'),
  });

  const validateMutation = useMutation({
    mutationFn: () => validateProject(numericProjectId),
    onSuccess: (result) => {
      if (result.valid) setNotice(`Validation passed · ${result.field_count} fields`);
      else setError((result.errors || []).map((i) => i.message).join(' | ') || 'Validation failed.');
    },
    onError: (e) => setError(e.message || 'Failed to validate.'),
  });

  const compileMutation = useMutation({
    mutationFn: () => compileProject(numericProjectId),
    onSuccess: (blob) => {
      downloadBlob(blob, `${project?.name || 'project'}.zip`);
      setNotice('PBIP archive downloaded.');
    },
    onError: (e) => setError(e.message || 'Failed to compile.'),
  });

  const createPageMutation = useMutation({
    mutationFn: (payload) => createProjectPage(numericProjectId, payload),
    onSuccess: async (created) => {
      setNotice(`Page "${created.name || created.page_name}" created.`);
      setSelectedPageId(created.pages?.[created.pages.length - 1]?.id || created.id);
      await queryClient.invalidateQueries({ queryKey: ['project', numericProjectId] });
    },
    onError: (e) => setError(e.message || 'Failed to create page.'),
  });

  const updatePageMutation = useMutation({
    mutationFn: ({ pageId, payload }) => updateProjectPage(numericProjectId, pageId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['project', numericProjectId] });
      setNotice('Page saved.');
    },
    onError: (e) => setError(e.message || 'Failed to update page.'),
  });

  const deletePageMutation = useMutation({
    mutationFn: (pageId) => deleteProjectPage(numericProjectId, pageId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['project', numericProjectId] });
      setNotice('Page deleted.');
      setSelectedPageId(null);
    },
    onError: (e) => setError(e.message || 'Failed to delete page.'),
  });

  const createVisualMutation = useMutation({
    mutationFn: (payload) => createProjectVisual(numericProjectId, selectedPageId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['project', numericProjectId] });
      setNotice('Visual added.');
      setVisualForm(blankVisual);
    },
    onError: (e) => setError(e.message || 'Failed to add visual.'),
  });

  const deleteVisualMutation = useMutation({
    mutationFn: (visualId) => deleteProjectVisual(numericProjectId, selectedPageId, visualId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['project', numericProjectId] });
      setNotice('Visual deleted.');
    },
    onError: (e) => setError(e.message || 'Failed to delete visual.'),
  });

  /* ── Handlers ──────────────────────────────────────────────── */

  const handleCreatePage = () => {
    createPageMutation.mutate({
      name: pageForm.name || `page_${pages.length + 1}`,
      display_name: pageForm.display_name || pageForm.name || `Page ${pages.length + 1}`,
      width: Number(pageForm.width) || 1280,
      height: Number(pageForm.height) || 720,
      page_order: pages.length,
      visuals: [],
      raw: {},
    });
  };

  const handleSavePage = () => {
    if (!selectedPage) return;
    updatePageMutation.mutate({
      pageId: selectedPage.id,
      payload: {
        name: pageForm.name || selectedPage.name,
        display_name: pageForm.display_name || selectedPage.display_name,
        width: Number(pageForm.width) || 1280,
        height: Number(pageForm.height) || 720,
      },
    });
  };

  const handleAddVisual = () => {
    if (!selectedPage) { setError('Create or select a page first.'); return; }
    let parsedBindings = {};
    let parsedConfig = {};
    try {
      parsedBindings = visualForm.bindings ? JSON.parse(visualForm.bindings) : {};
      parsedConfig = visualForm.config ? JSON.parse(visualForm.config) : {};
    } catch {
      setError('Visual bindings and config must be valid JSON.');
      return;
    }
    createVisualMutation.mutate({
      template_key: visualForm.template_key,
      name: visualForm.name,
      x: Number(visualForm.x) || 0,
      y: Number(visualForm.y) || 0,
      w: Number(visualForm.w) || 3,
      h: Number(visualForm.h) || 2,
      bindings: parsedBindings,
      config: parsedConfig,
      raw: {},
    });
  };

  /* ── Filtered fields for browser ───────────────────────────── */
  const filteredTables = useMemo(() => {
    const q = fieldSearch.toLowerCase();
    return (cachedFields?.tables || []).map((t) => ({
      ...t,
      fields: (t.fields || []).filter((f) =>
        !q || f.name?.toLowerCase().includes(q) || t.table?.toLowerCase().includes(q),
      ),
    })).filter((t) => t.fields.length > 0 || !q);
  }, [cachedFields, fieldSearch]);

  function normalizeField(field) {
    if (typeof field === 'string') {
      const [table = 'Unknown', name = ''] = field.split('.');
      return { table, name, kind: 'column', data_type: null, label: field };
    }
    const name = field.name || field.field || field.column || '';
    const kind = field.kind || field.field_type || field.type || 'column';
    return {
      table: field.table || field.table_name || 'Unknown',
      name,
      kind,
      data_type: field.data_type || field.dataType || null,
      label: field.label || `${field.table || field.table_name || 'Unknown'}.${name}`,
    };
  }

  function slotSupportsField(slot, field) {
    const slotType = slot.field_type || 'any';
    if (slotType === 'any') return true;
    if (slotType === 'measure') return field.kind === 'measure';
    if (slotType === 'column') return field.kind !== 'measure';
    return true;
  }

  function orderedSlots(template) {
    const slots = getTemplateSlots(template);
    return [...slots.filter((s) => s.required), ...slots.filter((s) => !s.required)];
  }

  const updateVisualBindingMutation = useMutation({
    mutationFn: ({ pageId, visualId, payload }) => updateProjectVisual(numericProjectId, pageId, visualId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['project', numericProjectId] });
      await queryClient.invalidateQueries({ queryKey: ['project-fields', numericProjectId] });
      setNotice('Visual bindings updated.');
    },
    onError: (e) => setError(e.message || 'Failed to update visual.'),
  });

  const handleAssignField = (field) => {
    if (!selectedPage || !selectedVisualId) {
      setNotice('Select a visual before assigning a field.');
      return;
    }

    const normalizedField = normalizeField(field);
    const visual = (selectedPage.visuals || []).find((v) => String(v.id) === String(selectedVisualId));
    if (!visual) {
      setError('Selected visual not found.');
      return;
    }

    const template = templates.find((t) => t.template_key === visual.template_key) || templates.find((t) => String(t.id) === String(visual.template_key)) || null;
    const candidateSlots = orderedSlots(template || { required_slots: [], optional_slots: [] }).filter((slot) => slotSupportsField(slot, normalizedField));
    if (!candidateSlots.length) {
      setError(`No available slot on ${template?.name || visual.template_key} can accept ${normalizedField.label}.`);
      return;
    }

    const currentBindings = { ...(visual.bindings || {}) };
    const targetSlot = candidateSlots.find((slot) => !currentBindings[slot.role] || (slot.multi && (!Array.isArray(currentBindings[slot.role]) || currentBindings[slot.role].length === 0))) || candidateSlots[0];

    if (targetSlot.multi) {
      const existing = Array.isArray(currentBindings[targetSlot.role]) ? currentBindings[targetSlot.role] : currentBindings[targetSlot.role] ? [currentBindings[targetSlot.role]] : [];
      const exists = existing.some((b) => (b.table || b.table_name) === normalizedField.table && (b.name || b.field || b.column) === normalizedField.name && (b.kind || b.field_type || b.type || 'column') === normalizedField.kind);
      if (exists) { setNotice(`${normalizedField.label} is already assigned.`); return; }
      currentBindings[targetSlot.role] = [...existing, normalizedField];
    } else {
      currentBindings[targetSlot.role] = normalizedField;
    }

    updateVisualBindingMutation.mutate({ pageId: selectedPage.id, visualId: visual.id, payload: { bindings: currentBindings } });
  };

  /* ── Guard ─────────────────────────────────────────────────── */
  if (!Number.isFinite(numericProjectId)) {
    return (
      <div className="page-content">
        <div className="empty-state">
          <div className="empty-state__title">Invalid project ID.</div>
        </div>
      </div>
    );
  }

  const isBusy = refreshMutation.isPending || validateMutation.isPending || compileMutation.isPending;

  return (
    <div className="page-content">
      {/* ── Hero ─────────────────────────────────────────────── */}
      <div className="page-hero">
        <div>
          <div className="page-hero__eyebrow">
            <BookOpen size={12} />
            Canvas report builder
          </div>
          <h1 className="page-hero__title">
            {project?.name || `Project ${projectId}`}
          </h1>
          <p className="page-hero__subtitle">
            Drag a starter visual onto the canvas, or pick a template from the gallery and bind semantic fields from the browser.
          </p>
        </div>
        <div className="page-hero__chips" style={{ gap: 8, alignItems: 'center' }}>
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => navigate('/projects')}
            style={{ color: 'rgba(255,255,255,0.8)', borderColor: 'rgba(255,255,255,0.2)', background: 'rgba(255,255,255,0.08)' }}
          >
            <ArrowLeft size={15} /> Back
          </button>
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => refreshMutation.mutate()}
            disabled={refreshMutation.isPending}
            style={{ color: 'rgba(255,255,255,0.8)', borderColor: 'rgba(255,255,255,0.2)', background: 'rgba(255,255,255,0.08)' }}
          >
            {refreshMutation.isPending ? <Loader2 size={14} style={{ animation: 'spin 0.7s linear infinite' }} /> : <RefreshCw size={14} />}
            Refresh
          </button>
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => validateMutation.mutate()}
            disabled={validateMutation.isPending}
            style={{ color: 'rgba(255,255,255,0.8)', borderColor: 'rgba(255,255,255,0.2)', background: 'rgba(255,255,255,0.08)' }}
          >
            {validateMutation.isPending ? <Loader2 size={14} style={{ animation: 'spin 0.7s linear infinite' }} /> : <ShieldCheck size={14} />}
            Validate
          </button>
          <button
            className="btn btn-primary"
            type="button"
            onClick={() => compileMutation.mutate()}
            disabled={compileMutation.isPending}
          >
            {compileMutation.isPending ? <Loader2 size={14} style={{ animation: 'spin 0.7s linear infinite' }} /> : <Download size={14} />}
            Compile PBIP
          </button>
        </div>
      </div>

      {/* ── Banners ───────────────────────────────────────────── */}
      {error && (
        <div className="status-banner status-banner--error">
          <span>{error}</span>
          <button className="status-banner__close" onClick={() => setError('')} type="button"><X size={14} /></button>
        </div>
      )}
      {notice && (
        <div className="status-banner status-banner--success">
          <span><CheckCircle2 size={14} style={{ display: 'inline', marginRight: 6 }} />{notice}</span>
          <button className="status-banner__close" onClick={() => setNotice('')} type="button"><X size={14} /></button>
        </div>
      )}

      {/* ── Validate result banner ────────────────────────────── */}
      {validateMutation.data && (
        <div className={`status-banner ${validateMutation.data.valid ? 'status-banner--success' : 'status-banner--error'}`}>
          {validateMutation.data.valid
            ? `✓ Validation passed · ${validateMutation.data.field_count} fields`
            : (validateMutation.data.errors || []).map((e) => e.message).join(' | ')}
        </div>
      )}

      {/* ── 3-col canvas layout ───────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '240px minmax(0,1fr) 280px', gap: 20, alignItems: 'start' }}>

        {/* Left: page list + add + metadata cache */}
        <div className="sticky-panel" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Pages list */}
          <div className="card">
            <div className="card-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="card-title">Pages</span>
              <span className="badge badge--purple">{pages.length}</span>
            </div>
            <div className="card-body" style={{ padding: '8px 0' }}>
              {pages.length === 0 ? (
                <div style={{ padding: '16px 20px', color: 'var(--muted)', fontSize: '0.82rem', textAlign: 'center' }}>
                  No pages yet
                </div>
              ) : (
                pages.map((page) => (
                  <button
                    key={page.id}
                    type="button"
                    onClick={() => setSelectedPageId(page.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      width: '100%',
                      padding: '10px 20px',
                      background: page.id === selectedPageId ? 'var(--purple-light)' : 'transparent',
                      border: 'none',
                      borderLeft: page.id === selectedPageId ? '3px solid var(--purple)' : '3px solid transparent',
                      cursor: 'pointer',
                      transition: 'all var(--transition)',
                      textAlign: 'left',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.875rem', color: page.id === selectedPageId ? 'var(--purple)' : 'var(--text)' }}>
                        {page.display_name || page.name}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: 2 }}>
                        {page.visuals?.length || 0} visuals
                      </div>
                    </div>
                    {page.id === selectedPageId && <ChevronRight size={14} style={{ color: 'var(--purple)' }} />}
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Add page */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Add Page</div>
            </div>
            <div className="card-body">
              <div className="form-stack">
                <div className="form-group">
                  <label className="form-label">Page name (key)</label>
                  <input
                    className="form-input"
                    value={pageForm.name}
                    onChange={(e) => setPageForm((c) => ({ ...c, name: e.target.value }))}
                    placeholder="e.g. sales_overview"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Display name</label>
                  <input
                    className="form-input"
                    value={pageForm.display_name}
                    onChange={(e) => setPageForm((c) => ({ ...c, display_name: e.target.value }))}
                    placeholder="e.g. Sales Overview"
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div className="form-group">
                    <label className="form-label">Width</label>
                    <input
                      className="form-input"
                      type="number"
                      value={pageForm.width}
                      onChange={(e) => setPageForm((c) => ({ ...c, width: e.target.value }))}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Height</label>
                    <input
                      className="form-input"
                      type="number"
                      value={pageForm.height}
                      onChange={(e) => setPageForm((c) => ({ ...c, height: e.target.value }))}
                    />
                  </div>
                </div>
                <button
                  className="btn btn-primary btn-full"
                  type="button"
                  onClick={handleCreatePage}
                  disabled={createPageMutation.isPending}
                >
                  {createPageMutation.isPending ? <Loader2 size={14} style={{ animation: 'spin 0.7s linear infinite' }} /> : <Plus size={14} />}
                  Add blank page
                </button>
              </div>
            </div>
          </div>

          {/* Metadata cache info */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Metadata cache</div>
              <div className="card-meta">{cachedFields?.fields?.length || 0} fields cached</div>
            </div>
            <div className="card-body" style={{ padding: '12px 16px' }}>
              {cachedFields?.debug?.metadata_status?.source && (
                <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginBottom: 8 }}>
                  Source: <strong>{cachedFields.debug.metadata_status.source}</strong>
                </div>
              )}
              {(cachedFields?.tables || []).slice(0, 6).map((t) => (
                <div key={t.table} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-2)', padding: '3px 0' }}>
                  <span><Database size={10} style={{ marginRight: 4, opacity: 0.5 }} />{t.table}</span>
                  <span className="badge badge--grey" style={{ padding: '1px 7px' }}>{t.fields?.length || 0}</span>
                </div>
              ))}
              {cachedFields?.debug?.xmla_error && (
                <div style={{ fontSize: '0.72rem', color: 'var(--danger)', marginTop: 8 }}>XMLA: {cachedFields.debug.xmla_error}</div>
              )}
            </div>
          </div>
        </div>

        {/* Center: canvas + selected page editor */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Page toolbar */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div className="canvas-toolbar">
              <div style={{ flex: 1, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {pages.map((page) => (
                  <button
                    key={page.id}
                    type="button"
                    className={`canvas-page-tab${page.id === selectedPageId ? ' canvas-page-tab--active' : ''}`}
                    onClick={() => setSelectedPageId(page.id)}
                  >
                    {page.display_name || page.name}
                  </button>
                ))}
                <button
                  type="button"
                  className="canvas-page-tab"
                  onClick={handleCreatePage}
                  style={{ borderStyle: 'dashed' }}
                >
                  <Plus size={12} /> Add page
                </button>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-ghost btn-sm" type="button" onClick={() => validateMutation.mutate()} disabled={validateMutation.isPending}>
                  <ShieldCheck size={13} /> Validate
                </button>
                <button className="btn btn-primary btn-sm" type="button" onClick={() => compileMutation.mutate()} disabled={compileMutation.isPending}>
                  <Zap size={13} /> Compile PBIP
                </button>
              </div>
            </div>

            {/* Drop zone (canvas area) */}
            <div className="canvas-drop-zone" style={{ minHeight: 320 }}>
              {!selectedPage ? (
                <div className="canvas-drop-zone--empty" style={{ minHeight: 320 }}>
                  <Layers size={40} style={{ opacity: 0.15 }} />
                  <div style={{ fontWeight: 700 }}>No page selected</div>
                  <div style={{ fontSize: '0.82rem' }}>Create a page using the panel on the left</div>
                </div>
              ) : (selectedPage.visuals || []).length === 0 ? (
                <div className="canvas-drop-zone--empty" style={{ minHeight: 320 }}>
                  <Layers size={40} style={{ opacity: 0.15 }} />
                  <div style={{ fontWeight: 700 }}>Empty page</div>
                  <div style={{ fontSize: '0.82rem' }}>Add visuals using the "Add Visual" panel →</div>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, alignContent: 'start' }}>
                  {(selectedPage.visuals || []).map((visual) => {
                        const VT = VISUAL_TYPES.find((v) => v.key === visual.template_key) || VISUAL_TYPES[0];
                        const isSelected = String(visual.id) === String(selectedVisualId);
                        return (
                          <div
                            key={visual.id}
                            className={`canvas-visual-block${isSelected ? ' canvas-visual-block--selected' : ''}`}
                            style={{ height: 160, position: 'relative', cursor: 'pointer' }}
                            onClick={() => setSelectedVisualId(visual.id)}
                          >
                            <div className="canvas-visual-block__title">{visual.name}</div>
                            <div className="canvas-visual-block__preview">
                              <VT.Icon size={36} style={{ opacity: 0.18 }} />
                            </div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>{visual.template_key} · {visual.w}×{visual.h}</div>
                            <button
                              type="button"
                              className="btn btn-danger btn-sm"
                              style={{ position: 'absolute', top: 8, right: 8, padding: '4px 8px' }}
                              onClick={() => deleteVisualMutation.mutate(visual.id)}
                            >
                              <Trash2 size={11} />
                            </button>
                          </div>
                        );
                      })}
                </div>
              )}
            </div>
          </div>

          {/* Edit selected page */}
          {selectedPage && (
            <div className="card">
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div className="card-title">Edit page</div>
                  <div className="card-meta">{selectedPage.display_name || selectedPage.name} · {selectedPage.visuals?.length || 0} visuals</div>
                </div>
                <button
                  className="btn btn-danger btn-sm"
                  type="button"
                  onClick={() => deletePageMutation.mutate(selectedPage.id)}
                  disabled={deletePageMutation.isPending}
                >
                  <Trash2 size={13} /> Delete page
                </button>
              </div>
              <div className="card-body">
                <div className="form-stack">
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    <div className="form-group">
                      <label className="form-label">Page key</label>
                      <input
                        className="form-input"
                        value={pageForm.name}
                        onChange={(e) => setPageForm((c) => ({ ...c, name: e.target.value }))}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Display name</label>
                      <input
                        className="form-input"
                        value={pageForm.display_name}
                        onChange={(e) => setPageForm((c) => ({ ...c, display_name: e.target.value }))}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Width px</label>
                      <input
                        className="form-input"
                        type="number"
                        value={pageForm.width}
                        onChange={(e) => setPageForm((c) => ({ ...c, width: e.target.value }))}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Height px</label>
                      <input
                        className="form-input"
                        type="number"
                        value={pageForm.height}
                        onChange={(e) => setPageForm((c) => ({ ...c, height: e.target.value }))}
                      />
                    </div>
                  </div>
                  <button
                    className="btn btn-primary"
                    type="button"
                    onClick={handleSavePage}
                    disabled={updatePageMutation.isPending}
                  >
                    {updatePageMutation.isPending ? <Loader2 size={14} style={{ animation: 'spin 0.7s linear infinite' }} /> : null}
                    Save page
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right: visual palette + field browser + add-visual form */}
        <div className="sticky-panel" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Visual Palette */}
          <div className="card">
            <div className="card-header"><div className="card-title">Visual Palette</div></div>
            <div className="card-body" style={{ padding: '8px 12px' }}>
              {VISUAL_TYPES.map((vt) => (
                <div
                  key={vt.key}
                  className="palette-visual-card"
                  onClick={() => setVisualForm((c) => ({ ...c, template_key: vt.key, name: vt.label }))}
                  title={`Select ${vt.label}`}
                  style={{ marginBottom: 8, border: visualForm.template_key === vt.key ? '1px solid var(--purple)' : undefined, background: visualForm.template_key === vt.key ? 'var(--purple-light)' : undefined }}
                >
                  <div className="palette-visual-card__icon"><vt.Icon size={14} /></div>
                  <div>
                    <div className="palette-visual-card__name">{vt.label}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Add visual form */}
          <div className="card">
            <div className="card-header"><div className="card-title">Add Visual</div></div>
            <div className="card-body">
              <div className="form-stack">
                <div className="form-group">
                  <label className="form-label">Visual name</label>
                  <input
                    className="form-input"
                    value={visualForm.name}
                    onChange={(e) => setVisualForm((c) => ({ ...c, name: e.target.value }))}
                    placeholder="Visual name"
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  {['x','y','w','h'].map((k) => (
                    <div className="form-group" key={k}>
                      <label className="form-label">{k.toUpperCase()}</label>
                      <input
                        className="form-input"
                        type="number"
                        value={visualForm[k]}
                        onChange={(e) => setVisualForm((c) => ({ ...c, [k]: e.target.value }))}
                      />
                    </div>
                  ))}
                </div>
                <div className="form-group">
                  <label className="form-label">Bindings JSON</label>
                  <textarea
                    className="form-input form-input--textarea"
                    style={{ minHeight: 64 }}
                    value={visualForm.bindings}
                    onChange={(e) => setVisualForm((c) => ({ ...c, bindings: e.target.value }))}
                    placeholder='{"axis":"Sales.Amount"}'
                  />
                </div>
                <button
                  className="btn btn-primary btn-full"
                  type="button"
                  onClick={handleAddVisual}
                  disabled={createVisualMutation.isPending || !selectedPage}
                >
                  {createVisualMutation.isPending ? <Loader2 size={14} style={{ animation: 'spin 0.7s linear infinite' }} /> : <Plus size={14} />}
                  Add visual
                </button>
              </div>
            </div>
          </div>

          {/* Field Browser */}
          <div className="card">
            <FieldBrowser fields={cachedFields?.fields || []} onAssignField={handleAssignField} selectedVisualId={selectedVisualId} />
          </div>

          {/* Project state */}
          <div className="card">
            <div className="card-header"><div className="card-title">Project state</div></div>
            <div className="card-body" style={{ padding: 0 }}>
              <div className="config-kv-list">
                <div className="config-kv-row">
                  <div className="config-kv-key">Model</div>
                  <div className="config-kv-value">{project?.source_semantic_model_name || '—'}</div>
                </div>
                <div className="config-kv-row">
                  <div className="config-kv-key">Pages</div>
                  <div className="config-kv-value">{pages.length}</div>
                </div>
                <div className="config-kv-row">
                  <div className="config-kv-key">Fields</div>
                  <div className="config-kv-value">{cachedFields?.fields?.length || 0}</div>
                </div>
                <div className="config-kv-row">
                  <div className="config-kv-key">Cache ver.</div>
                  <div className={`config-kv-value${project?.cache_version ? '' : ' config-kv-value--empty'}`}>
                    {project?.cache_version || 'None yet'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
