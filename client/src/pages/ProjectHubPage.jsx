import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  BarChart3,
  Calendar,
  Check,
  CircleX,
  Clock,
  FileStack,
  Layers,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
  X,
  Zap,
} from 'lucide-react';
import {
  createProject,
  deleteProject,
  listProjects,
  listSemanticModels,
  listWorkspaces,
  selectSemanticModel,
} from '../services/projectApi';
import { usePowerBi } from '../context/PowerBiContext';

const BAR_COLORS = ['purple', 'teal', 'blue', 'pink', 'amber'];

function StatusBadge({ status }) {
  const map = {
    compiled: { cls: 'badge--green', label: 'Compiled' },
    draft: { cls: 'badge--blue', label: 'Draft' },
    error: { cls: 'badge--red', label: 'Error' },
  };
  const entry = map[(status || 'draft').toLowerCase()] || map.draft;
  return <span className={`badge ${entry.cls}`}><span className="badge__dot" />{entry.label}</span>;
}

export default function ProjectsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { activeConnection, refreshConnections, setNotice } = usePowerBi();

  const [workspaceId, setWorkspaceId] = useState('');
  const [semanticModelRowId, setSemanticModelRowId] = useState('');
  const [semanticModelTouched, setSemanticModelTouched] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [error, setError] = useState('');
  const [localNotice, setLocalNotice] = useState('');
  const [showNewPanel, setShowNewPanel] = useState(false);

  const activeConnectionId = activeConnection?.id;

  const workspacesQuery = useQuery({
    queryKey: ['powerbi-workspaces', activeConnectionId],
    queryFn: () => listWorkspaces(activeConnectionId),
    enabled: Boolean(activeConnectionId),
  });

  const semanticModelsQuery = useQuery({
    queryKey: ['powerbi-semantic-models', activeConnectionId, workspaceId],
    queryFn: () => listSemanticModels(activeConnectionId, workspaceId),
    enabled: Boolean(activeConnectionId && workspaceId),
  });

  const projectsQuery = useQuery({
    queryKey: ['projects'],
    queryFn: listProjects,
  });

  const createProjectMutation = useMutation({
    mutationFn: createProject,
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: ['projects'] });
      setNotice(`Created ${created.name}.`);
      navigate(`/projects/${created.id}`);
    },
    onError: (e) => setError(e.message || 'Failed to create project.'),
  });

  const selectModelMutation = useMutation({
    mutationFn: ({ connectionId, workspace, model }) =>
      selectSemanticModel(connectionId, workspace, model),
    onSuccess: (selected) => {
      setLocalNotice(`Selected ${selected.semantic_model_name}.`);
      setSemanticModelRowId(String(selected.semantic_model_row_id));
      setSemanticModelTouched(true);
      refreshConnections();
    },
    onError: (e) => setError(e.message || 'Failed to select semantic model.'),
  });

  const deleteProjectMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['projects'] });
      setLocalNotice('Project deleted.');
    },
    onError: (e) => setError(e.message || 'Failed to delete project.'),
  });

  useEffect(() => {
    const workspaces = workspacesQuery.data || [];
    if (activeConnection?.active_workspace_id) {
      setWorkspaceId(activeConnection.active_workspace_id);
    } else if (!workspaceId && workspaces.length) {
      setWorkspaceId(workspaces[0].workspace_id || workspaces[0].id);
    } else if (!activeConnectionId) {
      setWorkspaceId('');
    }
  }, [activeConnection, activeConnectionId, workspaceId, workspacesQuery.data]);

  useEffect(() => {
    setSemanticModelTouched(false);
    setSemanticModelRowId('');
  }, [workspaceId]);

  useEffect(() => {
    if (!workspaceId) { setSemanticModelTouched(false); setSemanticModelRowId(''); return; }
    const semanticModels = semanticModelsQuery.data || [];
    const currentSelection = semanticModels.find((m) => String(m.id) === String(semanticModelRowId));
    if (currentSelection) return;
    if (!semanticModelTouched && activeConnection?.active_semantic_model_id) {
      const match = semanticModels.find((m) => (m.semantic_model_id || m.id) === activeConnection.active_semantic_model_id);
      setSemanticModelRowId(String(match?.id || activeConnection.active_semantic_model_id));
      return;
    }
    if (!semanticModelTouched && semanticModels.length) {
      setSemanticModelRowId(String(semanticModels[0].id));
    }
  }, [activeConnection, semanticModelRowId, semanticModelTouched, semanticModelsQuery.data, workspaceId]);

  const workspaces = useMemo(() => workspacesQuery.data || [], [workspacesQuery.data]);
  const semanticModels = useMemo(() => semanticModelsQuery.data || [], [semanticModelsQuery.data]);
  const projects = useMemo(() => projectsQuery.data || [], [projectsQuery.data]);

  const handleCreateProject = () => {
    if (!activeConnectionId) { setError('Create and select a Power BI connection first.'); return; }
    const selectedModel = semanticModels.find((m) => String(m.id) === String(semanticModelRowId));
    if (!workspaceId || !selectedModel) { setError('Choose a workspace and semantic model.'); return; }
    createProjectMutation.mutate({
      name: projectName.trim() || selectedModel.semantic_model_name || selectedModel.name || 'Project',
      source_semantic_model_id: Number(semanticModelRowId),
      canvas_settings: { width: 1280, height: 720 },
      report_settings: { themeName: 'BIFoundryTheme', themeColor: '#154360' },
      raw: {
        connection_id: activeConnectionId,
        session_id: activeConnection?.session?.id,
        workspace_id: workspaceId,
        semantic_model_id: selectedModel.semantic_model_id || selectedModel.id,
        semantic_model_row_id: semanticModelRowId,
      },
      pages: [],
    });
  };

  const handleSelectModel = () => {
    const selectedModel = semanticModels.find((m) => String(m.id) === String(semanticModelRowId));
    if (!activeConnectionId || !workspaceId || !selectedModel) return;
    selectModelMutation.mutate({
      connectionId: activeConnectionId,
      workspace: workspaceId,
      model: selectedModel.semantic_model_id || selectedModel.id,
    });
  };

  const handleDeleteProject = (projectId) => {
    if (window.confirm('Delete this project?')) deleteProjectMutation.mutate(projectId);
  };

  const compiledCount = projects.filter((p) => p.status === 'compiled').length;
  const draftCount = projects.filter((p) => !p.status || p.status === 'draft').length;

  return (
    <div className="page-content">
      {/* Hero */}
      <div className="page-hero">
        <div>
          <div className="page-hero__eyebrow">
            <BarChart3 size={12} />
            Report Builder
          </div>
          <h1 className="page-hero__title">Projects</h1>
          <p className="page-hero__subtitle">
            Create page-by-page Power BI report projects from your connected workspace and
            semantic model. Compile to PBIP format when ready.
          </p>
        </div>
        <div className="page-hero__chips">
          <div className="hero-chip">
            <Layers size={12} />
            {projects.length} project{projects.length !== 1 ? 's' : ''}
          </div>
          <div className="hero-chip">
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', display: 'inline-block' }} />
            {activeConnection?.label || 'No connection'}
          </div>
        </div>
      </div>

      {/* Banners */}
      {error && (
        <div className="status-banner status-banner--error">
          <span><CircleX size={15} style={{ display: 'inline', marginRight: 6 }} />{error}</span>
          <button className="status-banner__close" onClick={() => setError('')} type="button"><X size={14} /></button>
        </div>
      )}
      {localNotice && (
        <div className="status-banner status-banner--success">
          <span><Check size={15} style={{ display: 'inline', marginRight: 6 }} />{localNotice}</span>
          <button className="status-banner__close" onClick={() => setLocalNotice('')} type="button"><X size={14} /></button>
        </div>
      )}
      {!activeConnection && (
        <div className="status-banner status-banner--info">
          Connect a Power BI profile in the Connections page before creating projects.
        </div>
      )}

      {/* Stats Row */}
      <div className="stat-row">
        {[
          { label: 'Total Projects', value: projects.length, color: 'purple' },
          { label: 'Compiled', value: compiledCount, color: 'teal' },
          { label: 'Drafts', value: draftCount, color: 'blue' },
          { label: 'Workspaces Loaded', value: workspaces.length, color: 'pink' },
        ].map((s) => (
          <div key={s.label} className={`stat-card stat-card--${s.color}`}>
            <div className="stat-card__label">{s.label}</div>
            <div className="stat-card__value">{s.value}</div>
          </div>
        ))}
      </div>

      {/* Content */}
      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
        {/* Projects grid */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div className="section-label" style={{ marginBottom: 0 }}>All Projects</div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-ghost" onClick={() => navigate('/create')} type="button">
                <FileStack size={15} />
                Use Wizard
              </button>
              <button className="btn btn-primary" onClick={() => setShowNewPanel(true)} type="button">
                <Plus size={16} />
                New Project
              </button>
            </div>
          </div>

          {projectsQuery.isLoading ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '24px 0', color: 'var(--muted)' }}>
              <Loader2 size={18} style={{ animation: 'spin 0.7s linear infinite' }} /> Loading projects...
            </div>
          ) : projects.length === 0 ? (
            <div className="card card--md">
              <div className="empty-state">
                <div className="empty-state__icon"><BarChart3 size={24} /></div>
                <div className="empty-state__title">No projects yet</div>
                <div className="empty-state__body">
                  Create your first Power BI report project to get started.
                </div>
                <button className="btn btn-primary" onClick={() => setShowNewPanel(true)} type="button">
                  <Plus size={15} /> Create Project
                </button>
              </div>
            </div>
          ) : (
            <div className="cards-grid">
              {projects.map((project, idx) => {
                const color = BAR_COLORS[idx % BAR_COLORS.length];
                return (
                  <div key={project.id} className="project-card">
                    <div className={`project-card__bar project-card__bar--${color}`} />
                    <div className="project-card__body">
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
                        <div className="project-card__title">{project.name}</div>
                        <StatusBadge status={project.status} />
                      </div>
                      <div className="project-card__model">
                        {project.source_semantic_model_name || 'No semantic model'}
                      </div>
                      <div className="project-card__meta-row">
                        <div className="project-card__meta-item">
                          <Layers size={12} />
                          {project.pages?.length ?? 0} page{(project.pages?.length ?? 0) !== 1 ? 's' : ''}
                        </div>
                        {project.updated_at && (
                          <div className="project-card__meta-item">
                            <Clock size={12} />
                            {new Date(project.updated_at).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                      <div className="project-card__actions">
                        <button
                          className="btn btn-primary btn-sm"
                          type="button"
                          onClick={() => navigate(`/projects/${project.id}`)}
                        >
                          Open Editor
                        </button>
                        <button className="btn btn-teal btn-sm" type="button">
                          <Zap size={13} />
                          Compile
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          type="button"
                          style={{ marginLeft: 'auto' }}
                          onClick={() => handleDeleteProject(project.id)}
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Active connection summary */}
        <div style={{ width: 280, flexShrink: 0 }} className="sticky-panel">
          <div className="section-label">Active Connection</div>
          <div className="panel-card">
            <div className="panel-card__title">{activeConnection?.label || 'No connection selected'}</div>
            <div className="panel-card__body">
              {activeConnection?.owner_user_email || activeConnection?.owner_user_name || 'Open Connections to create or switch profiles.'}
            </div>
            <div className="panel-card__kv" style={{ marginTop: 12 }}>
              <div className="panel-card__kv-row">
                <div className="panel-card__kv-label">Workspace</div>
                <div className="panel-card__kv-value">{activeConnection?.active_workspace_name || activeConnection?.active_workspace_id || 'Not selected'}</div>
              </div>
              <div className="panel-card__kv-row">
                <div className="panel-card__kv-label">Model</div>
                <div className="panel-card__kv-value">{activeConnection?.active_semantic_model_name || activeConnection?.active_semantic_model_id || 'Not selected'}</div>
              </div>
            </div>
            <div className="mt-3">
              <button className="btn btn-ghost btn-sm btn-full" onClick={() => navigate('/connections')} type="button">
                Manage Connections
              </button>
            </div>
          </div>

          <div className="section-label" style={{ marginTop: 16 }}>Workflow</div>
          <div className="panel-card">
            <div className="panel-card__title">Stage-based Flow</div>
            <div className="panel-card__body">
              {['Create a Power BI connection.', 'Sign in through the profile.', 'Choose workspace & semantic model.', 'Create pages, then compile.'].map((s, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'flex-start' }}>
                  <span style={{ fontWeight: 800, color: 'var(--purple)', flexShrink: 0 }}>{i + 1}.</span>
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* New Project slide-in panel */}
      <div className={`panel-overlay${showNewPanel ? ' panel-overlay--active' : ''}`}>
        <div className="panel-backdrop" onClick={() => setShowNewPanel(false)} />
        <div className="slide-panel">
          <div className="slide-panel__header">
            <div className="slide-panel__title">New Project</div>
            <button className="btn btn-icon btn-ghost" type="button" onClick={() => setShowNewPanel(false)}>
              <X size={18} />
            </button>
          </div>
          <div className="slide-panel__body">
            <div className="form-stack">
              <div className="form-group">
                <label className="form-label" htmlFor="proj-name">Project Name</label>
                <input
                  id="proj-name"
                  className="form-input"
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="My Sales Report"
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="proj-workspace">Workspace</label>
                <select
                  id="proj-workspace"
                  className="form-input form-select"
                  value={workspaceId}
                  onChange={(e) => setWorkspaceId(e.target.value)}
                  disabled={!activeConnectionId}
                >
                  <option value="">Choose workspace</option>
                  {workspaces.map((ws) => (
                    <option key={ws.workspace_id || ws.id} value={ws.workspace_id || ws.id}>
                      {ws.name || ws.workspace_name || ws.workspace_id}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="proj-model">Semantic Model</label>
                <select
                  id="proj-model"
                  className="form-input form-select"
                  value={semanticModelRowId}
                  onChange={(e) => { setSemanticModelTouched(true); setSemanticModelRowId(e.target.value); }}
                  disabled={!workspaceId}
                >
                  <option value="">Choose semantic model</option>
                  {semanticModels.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.semantic_model_name || m.name || m.semantic_model_id}
                    </option>
                  ))}
                </select>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-ghost btn-sm" type="button" onClick={() => workspacesQuery.refetch()} disabled={!activeConnectionId}>
                  <RefreshCw size={13} /> Workspaces
                </button>
                <button className="btn btn-ghost btn-sm" type="button" onClick={() => semanticModelsQuery.refetch()} disabled={!workspaceId}>
                  <RefreshCw size={13} /> Models
                </button>
              </div>
              <button className="btn btn-teal btn-full" type="button" onClick={handleSelectModel} disabled={!workspaceId || !semanticModelRowId}>
                <Check size={15} /> Set Active Model
              </button>
            </div>
          </div>
          <div className="slide-panel__footer">
            <button
              className="btn btn-primary"
              type="button"
              onClick={handleCreateProject}
              disabled={createProjectMutation.isPending}
              style={{ flex: 1 }}
            >
              {createProjectMutation.isPending ? <Loader2 size={15} style={{ animation: 'spin 0.7s linear infinite' }} /> : <Plus size={15} />}
              Create Project
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
