import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  createProject,
  deleteProject,
  listProjects,
  listSemanticModels,
  listWorkspaces,
  selectSemanticModel,
} from '../services/projectApi';
import { usePowerBi } from '../context/PowerBiContext';

export default function ProjectsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { activeConnection, refreshConnections, setNotice } = usePowerBi();
  const [workspaceId, setWorkspaceId] = useState('');
  const [semanticModelRowId, setSemanticModelRowId] = useState('');
  const [semanticModelTouched, setSemanticModelTouched] = useState(false);
  const [projectName, setProjectName] = useState('Untitled Project');
  const [error, setError] = useState('');

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
    onError: (requestError) => setError(requestError.message || 'Failed to create project.'),
  });

  const selectModelMutation = useMutation({
    mutationFn: ({ connectionId, workspace, model }) => selectSemanticModel(connectionId, workspace, model),
    onSuccess: (selected) => {
      setNotice(`Selected ${selected.semantic_model_name}.`);
      setSemanticModelRowId(String(selected.semantic_model_row_id));
      setSemanticModelTouched(true);
      refreshConnections();
    },
    onError: (requestError) => setError(requestError.message || 'Failed to select semantic model.'),
  });

  const deleteProjectMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
    onError: (requestError) => setError(requestError.message || 'Failed to delete project.'),
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
    if (!workspaceId) {
      setSemanticModelTouched(false);
      setSemanticModelRowId('');
      return;
    }

    const semanticModels = semanticModelsQuery.data || [];
    const currentSelection = semanticModels.find((model) => String(model.id) === String(semanticModelRowId));

    if (currentSelection) {
      return;
    }

    if (!semanticModelTouched && activeConnection?.active_semantic_model_id) {
      const match = semanticModels.find((model) => (model.semantic_model_id || model.id) === activeConnection.active_semantic_model_id);
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
    if (!activeConnectionId) {
      setError('Create and select a Power BI connection first.');
      return;
    }
    const selectedModel = semanticModels.find((model) => String(model.id) === String(semanticModelRowId));
    if (!workspaceId || !selectedModel) {
      setError('Choose a workspace and semantic model.');
      return;
    }

    createProjectMutation.mutate({
      name: projectName.trim() || 'Untitled Project',
      source_semantic_model_id: Number(semanticModelRowId),
      canvas_settings: {
        width: 1280,
        height: 720,
      },
      report_settings: {
        themeName: 'BIFoundryTheme',
        themeColor: '#154360',
      },
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
    const selectedModel = semanticModels.find((model) => String(model.id) === String(semanticModelRowId));
    if (!activeConnectionId || !workspaceId || !selectedModel) {
      return;
    }
    selectModelMutation.mutate({ connectionId: activeConnectionId, workspace: workspaceId, model: selectedModel.semantic_model_id || selectedModel.id });
  };

  const handleDeleteProject = (projectId) => {
    if (window.confirm('Delete this project?')) {
      deleteProjectMutation.mutate(projectId);
    }
  };

  return (
    <div className="page-stack">
      <header className="hero">
        <div className="hero__content">
          <div className="eyebrow">BIFoundry</div>
          <h1>Projects</h1>
          <p>Create page-by-page project shells from the selected Power BI connection, workspace, and semantic model.</p>
        </div>
        <div className="hero__status">
          <div className="status-chip">{activeConnection?.label || 'No active connection'}</div>
          <div className="status-chip status-chip--muted">{workspaces.length ? `${workspaces.length} workspaces` : 'No workspaces loaded'}</div>
          <div className="status-chip status-chip--muted">{projects.length ? `${projects.length} projects` : 'No projects yet'}</div>
        </div>
      </header>

      {error ? <div className="status-banner status-banner--error">{error}</div> : null}
      {activeConnection ? null : <div className="status-banner status-banner--info">Create a Power BI connection in the Connections page before you create projects.</div>}

      <main className="workspace page-grid page-grid--builder">
        <section className="project-panel">
          <div className="section-title">Connection</div>
          <div className="panel-card">
            <div className="panel-card__title">{activeConnection?.label || 'No connection selected'}</div>
            <div className="helper-text">
              {activeConnection?.owner_user_email || activeConnection?.owner_user_name || 'Open Power BI Connections to create or switch profiles.'}
            </div>
            <div className="stack">
              <button className="button button--primary" type="button" onClick={() => navigate('/connections')}>
                Manage connections
              </button>
              <button className="button" type="button" onClick={() => refreshConnections()}>
                Refresh profiles
              </button>
            </div>
          </div>

          <div className="section-title">Projects</div>
          <div className="list">
            {projects.map((project) => (
              <div key={project.id} className="panel-card">
                <div className="panel-card__title">{project.name}</div>
                <div className="helper-text">{project.source_semantic_model_name || 'No semantic model selected'}</div>
                <div className="stack">
                  <button className="button button--primary" type="button" onClick={() => navigate(`/projects/${project.id}`)}>
                    Open project
                  </button>
                  <button className="button" type="button" onClick={() => handleDeleteProject(project.id)}>
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="canvas-shell">
          <div className="canvas-shell__header">
            <div>
              <div className="section-title">New project</div>
              <div className="canvas-shell__subtitle">Pick the active workspace and semantic model, then create a project shell.</div>
            </div>
          </div>
          <div className="stack">
            <input
              className="input"
              type="text"
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
              placeholder="Project name"
            />
            <select className="input" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)} disabled={!activeConnectionId}>
              <option value="">Choose workspace</option>
              {workspaces.map((workspace) => (
                <option key={workspace.workspace_id || workspace.id} value={workspace.workspace_id || workspace.id}>
                  {workspace.name || workspace.workspace_name || workspace.workspace_id}
                </option>
              ))}
            </select>
            <select
              className="input"
              value={semanticModelRowId}
              onChange={(event) => {
                setSemanticModelTouched(true);
                setSemanticModelRowId(event.target.value);
              }}
              disabled={!workspaceId}
            >
              <option value="">Choose semantic model</option>
              {semanticModels.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.semantic_model_name || model.name || model.semantic_model_id}
                </option>
              ))}
            </select>
            <div className="stack">
              <button className="button" type="button" onClick={() => workspacesQuery.refetch()} disabled={!activeConnectionId}>
                Refresh workspaces
              </button>
              <button className="button" type="button" onClick={() => semanticModelsQuery.refetch()} disabled={!workspaceId}>
                Refresh semantic models
              </button>
              <button className="button button--primary" type="button" onClick={handleSelectModel} disabled={!workspaceId || !semanticModelRowId}>
                Select semantic model
              </button>
              <button className="button button--primary" type="button" onClick={handleCreateProject} disabled={createProjectMutation.isPending}>
                Create project
              </button>
            </div>
          </div>
        </section>

        <section className="properties-panel">
          <div className="section-title">Workflow</div>
          <div className="panel-card">
            <div className="panel-card__title">Stage-based flow</div>
            <div className="helper-text">
              1. Create a Power BI connection.
              <br />
              2. Sign in through the connection profile.
              <br />
              3. Choose a workspace and semantic model.
              <br />
              4. Open a project page, refresh metadata, add pages, then compile.
            </div>
          </div>
          <div className="section-title">Selected model</div>
          <div className="panel-card">
            <div className="panel-card__title">
              {semanticModelsQuery.isFetching ? 'Loading...' : semanticModels.find((model) => String(model.id) === String(semanticModelRowId))?.semantic_model_name || 'No model selected'}
            </div>
            <div className="helper-text">
              {workspaceId ? `Workspace: ${workspaces.find((workspace) => (workspace.workspace_id || workspace.id) === workspaceId)?.name || workspaceId}` : 'Choose a workspace first.'}
            </div>
          </div>
          <div className="section-title">Active profile</div>
          <div className="panel-card">
            <div className="panel-card__title">{activeConnection?.label || 'No connection'}</div>
            <div className="helper-text">{activeConnection?.session?.user_email || activeConnection?.owner_user_email || 'Not authenticated yet.'}</div>
          </div>
        </section>
      </main>
    </div>
  );
}
