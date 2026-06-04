import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
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
} from '../services/projectApi';

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
  const [pageForm, setPageForm] = useState({
    name: '',
    display_name: '',
    width: 1280,
    height: 720,
  });
  const [visualForm, setVisualForm] = useState(blankVisual);

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
    if (pages.length && !selectedPageId) {
      setSelectedPageId(pages[0].id);
    }
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

  const refreshMutation = useMutation({
    mutationFn: () => refreshProjectMetadata(numericProjectId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['project', numericProjectId] });
      await queryClient.invalidateQueries({ queryKey: ['project-fields', numericProjectId] });
      setNotice('Project metadata refreshed.');
    },
    onError: (requestError) => setError(requestError.message || 'Failed to refresh metadata.'),
  });

  const validateMutation = useMutation({
    mutationFn: () => validateProject(numericProjectId),
    onSuccess: (result) => {
      if (result.valid) {
        setNotice(`Validation passed with ${result.field_count} fields.`);
      } else {
        setError((result.errors || []).map((item) => item.message).join(' | ') || 'Validation failed.');
      }
    },
    onError: (requestError) => setError(requestError.message || 'Failed to validate project.'),
  });

  const compileMutation = useMutation({
    mutationFn: () => compileProject(numericProjectId),
    onSuccess: (blob) => {
      downloadBlob(blob, `${project?.name || 'project'}.zip`);
      setNotice('PBIP archive generated.');
    },
    onError: (requestError) => setError(requestError.message || 'Failed to compile project.'),
  });

  const createPageMutation = useMutation({
    mutationFn: (payload) => createProjectPage(numericProjectId, payload),
    onSuccess: async (created) => {
      setNotice(`Created page ${created.name || created.page_name}.`);
      setSelectedPageId(created.pages?.[created.pages.length - 1]?.id || created.id);
      await queryClient.invalidateQueries({ queryKey: ['project', numericProjectId] });
    },
    onError: (requestError) => setError(requestError.message || 'Failed to create page.'),
  });

  const updatePageMutation = useMutation({
    mutationFn: ({ pageId, payload }) => updateProjectPage(numericProjectId, pageId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['project', numericProjectId] });
      setNotice('Page saved.');
    },
    onError: (requestError) => setError(requestError.message || 'Failed to update page.'),
  });

  const deletePageMutation = useMutation({
    mutationFn: (pageId) => deleteProjectPage(numericProjectId, pageId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['project', numericProjectId] });
      setNotice('Page deleted.');
      setSelectedPageId(null);
    },
    onError: (requestError) => setError(requestError.message || 'Failed to delete page.'),
  });

  const createVisualMutation = useMutation({
    mutationFn: (payload) => createProjectVisual(numericProjectId, selectedPageId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['project', numericProjectId] });
      setNotice('Visual added.');
      setVisualForm(blankVisual);
    },
    onError: (requestError) => setError(requestError.message || 'Failed to add visual.'),
  });

  const deleteVisualMutation = useMutation({
    mutationFn: (visualId) => deleteProjectVisual(numericProjectId, selectedPageId, visualId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['project', numericProjectId] });
      setNotice('Visual deleted.');
    },
    onError: (requestError) => setError(requestError.message || 'Failed to delete visual.'),
  });

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
    if (!selectedPage) {
      return;
    }
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
    if (!selectedPage) {
      setError('Create or select a page first.');
      return;
    }
    let parsedBindings = {};
    let parsedConfig = {};
    try {
      parsedBindings = visualForm.bindings ? JSON.parse(visualForm.bindings) : {};
      parsedConfig = visualForm.config ? JSON.parse(visualForm.config) : {};
    } catch (requestError) {
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

  if (!Number.isFinite(numericProjectId)) {
    return <div className="app-shell">Invalid project id.</div>;
  }

  return (
    <div className="page-stack">
      <header className="hero">
        <div className="hero__content">
          <div className="eyebrow">Project editor</div>
          <h1>{project?.name || `Project ${projectId}`}</h1>
          <p>Refresh the cached semantic metadata on demand, add report pages one by one, and compile the saved configuration into a PBIP package.</p>
        </div>
        <div className="hero__status">
          <button className="button button--ghost" type="button" onClick={() => navigate('/projects')}>
            Back to projects
          </button>
          <button className="button" type="button" onClick={() => refreshMutation.mutate()} disabled={refreshMutation.isPending}>
            Refresh metadata
          </button>
          <button className="button" type="button" onClick={() => validateMutation.mutate()} disabled={validateMutation.isPending}>
            Validate
          </button>
          <button className="button button--primary" type="button" onClick={() => compileMutation.mutate()} disabled={compileMutation.isPending}>
            Compile PBIP
          </button>
        </div>
      </header>

      {error ? <div className="status-banner status-banner--error">{error}</div> : null}
      {notice ? <div className="status-banner status-banner--success">{notice}</div> : null}

      <main className="workspace page-grid page-grid--builder">
        <section className="project-panel">
          <div className="section-title">Pages</div>
          <div className="list">
            {pages.map((page) => (
              <button
                key={page.id}
                type="button"
                className={`menu-tab ${page.id === selectedPageId ? 'menu-tab--active' : ''}`}
                onClick={() => setSelectedPageId(page.id)}
              >
                <span className="menu-tab__label">{page.display_name || page.name}</span>
                <span className="menu-tab__meta">{page.visuals?.length || 0} visuals</span>
              </button>
            ))}
          </div>

          <div className="section-title">Add page</div>
          <div className="panel-card">
            <div className="stack">
              <input
                className="input"
                value={pageForm.name}
                onChange={(event) => setPageForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Page name"
              />
              <input
                className="input"
                value={pageForm.display_name}
                onChange={(event) => setPageForm((current) => ({ ...current, display_name: event.target.value }))}
                placeholder="Display name"
              />
              <div className="split-form">
                <input
                  className="input"
                  type="number"
                  value={pageForm.width}
                  onChange={(event) => setPageForm((current) => ({ ...current, width: event.target.value }))}
                  placeholder="Width"
                />
                <input
                  className="input"
                  type="number"
                  value={pageForm.height}
                  onChange={(event) => setPageForm((current) => ({ ...current, height: event.target.value }))}
                  placeholder="Height"
                />
              </div>
              <button className="button button--primary" type="button" onClick={handleCreatePage} disabled={createPageMutation.isPending}>
                Add page
              </button>
            </div>
          </div>

          <div className="section-title">Metadata cache</div>
          <div className="panel-card">
            <div className="panel-card__title">Fields</div>
            <div className="helper-text">{cachedFields?.fields?.length || 0} cached fields</div>
            {cachedFields?.debug?.metadata_status?.source ? (
              <div className="helper-text">Metadata source: {cachedFields.debug.metadata_status.source}</div>
            ) : null}
            {cachedFields?.debug?.admin_scan_error ? (
              <div className="helper-text" style={{ marginTop: '0.75rem', color: '#9f3a38' }}>
                Admin scan error: {cachedFields.debug.admin_scan_error}
              </div>
            ) : null}
            {cachedFields?.debug?.admin_scan_status ? (
              <div className="helper-text">Admin scan status: {cachedFields.debug.admin_scan_status}</div>
            ) : null}
            <div className="mini-summary">
              {(cachedFields?.tables || []).slice(0, 6).map((table) => (
                <div key={table.table}>
                  {table.table}: {table.fields.length}
                </div>
              ))}
            </div>
            {cachedFields?.debug?.xmla_error ? (
              <div className="helper-text" style={{ marginTop: '0.75rem', color: '#9f3a38' }}>
                XMLA error: {cachedFields.debug.xmla_error}
              </div>
            ) : null}
            {cachedFields?.debug?.dax_error ? (
              <div className="helper-text" style={{ marginTop: '0.75rem', color: '#9f3a38' }}>
                DAX metadata error: {cachedFields.debug.dax_error}
              </div>
            ) : null}
            {cachedFields?.debug?.dax_query_failures && Object.keys(cachedFields.debug.dax_query_failures).length ? (
              <pre className="code-block">{JSON.stringify(cachedFields.debug.dax_query_failures, null, 2)}</pre>
            ) : null}
            {cachedFields?.debug?.metadata_status ? (
              <pre className="code-block">{JSON.stringify(cachedFields.debug.metadata_status, null, 2)}</pre>
            ) : null}
          </div>
        </section>

        <section className="canvas-shell">
          <div className="canvas-shell__header">
            <div>
              <div className="section-title">Selected page</div>
              <div className="canvas-shell__subtitle">
                {selectedPage ? `${selectedPage.display_name || selectedPage.name} · ${selectedPage.visuals?.length || 0} visuals` : 'Create a page to start.'}
              </div>
            </div>
          </div>

          {selectedPage ? (
            <div className="stack">
              <div className="panel-card">
                <div className="panel-card__title">Edit page</div>
                <div className="stack">
                  <input
                    className="input"
                    value={pageForm.name}
                    onChange={(event) => setPageForm((current) => ({ ...current, name: event.target.value }))}
                    placeholder="Page name"
                  />
                  <input
                    className="input"
                    value={pageForm.display_name}
                    onChange={(event) => setPageForm((current) => ({ ...current, display_name: event.target.value }))}
                    placeholder="Display name"
                  />
                  <div className="split-form">
                    <input
                      className="input"
                      type="number"
                      value={pageForm.width}
                      onChange={(event) => setPageForm((current) => ({ ...current, width: event.target.value }))}
                    />
                    <input
                      className="input"
                      type="number"
                      value={pageForm.height}
                      onChange={(event) => setPageForm((current) => ({ ...current, height: event.target.value }))}
                    />
                  </div>
                  <div className="stack">
                    <button className="button button--primary" type="button" onClick={handleSavePage} disabled={updatePageMutation.isPending}>
                      Save page
                    </button>
                    <button className="button button--danger" type="button" onClick={() => deletePageMutation.mutate(selectedPage.id)} disabled={deletePageMutation.isPending}>
                      Delete page
                    </button>
                  </div>
                </div>
              </div>

              <div className="panel-card">
                <div className="panel-card__title">Visuals</div>
                <div className="list">
                  {(selectedPage.visuals || []).map((visual) => (
                    <div key={visual.id} className="visual-mini">
                      <div>
                        <strong>{visual.name}</strong>
                        <div className="helper-text">{visual.template_key} · {visual.w} x {visual.h}</div>
                      </div>
                      <button className="button button--danger button--small" type="button" onClick={() => deleteVisualMutation.mutate(visual.id)}>
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="panel-card">
                <div className="panel-card__title">Add visual</div>
                <div className="stack">
                  <input
                    className="input"
                    value={visualForm.template_key}
                    onChange={(event) => setVisualForm((current) => ({ ...current, template_key: event.target.value }))}
                    placeholder="Template key"
                  />
                  <input
                    className="input"
                    value={visualForm.name}
                    onChange={(event) => setVisualForm((current) => ({ ...current, name: event.target.value }))}
                    placeholder="Visual name"
                  />
                  <div className="split-form">
                    <input className="input" type="number" value={visualForm.x} onChange={(event) => setVisualForm((current) => ({ ...current, x: event.target.value }))} placeholder="x" />
                    <input className="input" type="number" value={visualForm.y} onChange={(event) => setVisualForm((current) => ({ ...current, y: event.target.value }))} placeholder="y" />
                    <input className="input" type="number" value={visualForm.w} onChange={(event) => setVisualForm((current) => ({ ...current, w: event.target.value }))} placeholder="w" />
                    <input className="input" type="number" value={visualForm.h} onChange={(event) => setVisualForm((current) => ({ ...current, h: event.target.value }))} placeholder="h" />
                  </div>
                  <textarea
                    className="input input--textarea"
                    value={visualForm.bindings}
                    onChange={(event) => setVisualForm((current) => ({ ...current, bindings: event.target.value }))}
                    placeholder='Bindings JSON, for example {"axis":"Sales.Amount"}'
                  />
                  <textarea
                    className="input input--textarea"
                    value={visualForm.config}
                    onChange={(event) => setVisualForm((current) => ({ ...current, config: event.target.value }))}
                    placeholder='Config JSON'
                  />
                  <button className="button button--primary" type="button" onClick={handleAddVisual} disabled={createVisualMutation.isPending}>
                    Add visual
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state empty-state--canvas">Create a page to start laying out visuals.</div>
          )}
        </section>

        <section className="properties-panel">
          <div className="section-title">Project state</div>
          <div className="panel-card">
            <div className="panel-card__title">{project?.name || 'Loading...'}</div>
            <div className="helper-text">
              Source model: {project?.source_semantic_model_name || 'Not selected'}
              <br />
              Cache version: {project?.cache_version || 'None yet'}
            </div>
          </div>
          <div className="section-title">Validation</div>
          <div className="panel-card">
            <div className="panel-card__title">Last result</div>
            <pre className="code-block">{JSON.stringify(validateMutation.data || {}, null, 2)}</pre>
          </div>
        </section>
      </main>
    </div>
  );
}
