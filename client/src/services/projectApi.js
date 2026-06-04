const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      ...(options.body && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      if (typeof payload.detail === 'string') {
        detail = payload.detail;
      } else if (payload.detail && typeof payload.detail === 'object') {
        const message = payload.detail.message || payload.message || detail;
        const extras = { ...payload.detail };
        delete extras.message;
        detail = Object.keys(extras).length ? `${message} ${JSON.stringify(extras)}` : message;
      } else {
        detail = payload.message || detail;
      }
    } catch (error) {
      try {
        detail = await response.text();
      } catch (_readError) {
        // keep default detail
      }
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }

  return response;
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function getPowerBiConfig() {
  return request('/powerbi/config');
}

export function listPowerBiConnections() {
  return request('/powerbi/connections');
}

export function getPowerBiConnection(connectionId) {
  return request(`/powerbi/connections/${connectionId}`);
}

export function createPowerBiConnection(payload) {
  return request('/powerbi/connections', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updatePowerBiConnection(connectionId, payload) {
  return request(`/powerbi/connections/${connectionId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deletePowerBiConnection(connectionId) {
  return request(`/powerbi/connections/${connectionId}`, {
    method: 'DELETE',
  });
}

export function selectPowerBiConnection(connectionId) {
  return request(`/powerbi/connections/${connectionId}/select`, {
    method: 'POST',
  });
}

export function refreshPowerBiConnection(connectionId) {
  return request(`/powerbi/connections/${connectionId}/refresh`, {
    method: 'POST',
  });
}

export function startPowerBiLogin(connectionId) {
  return request(`/powerbi/connections/${connectionId}/auth/login`, {
    method: 'POST',
    body: JSON.stringify({ connection_id: connectionId }),
  });
}

export function getPowerBiSession(sessionId) {
  return request(`/powerbi/auth/session/${sessionId}`);
}

export function refreshPowerBiSession(sessionId) {
  return request(`/powerbi/auth/session/${sessionId}/refresh`, { method: 'POST' });
}

export function deletePowerBiSession(sessionId) {
  return request(`/powerbi/auth/session/${sessionId}`, { method: 'DELETE' });
}

export function listWorkspaces(connectionId) {
  return request('/powerbi/workspaces', {
    headers: { 'X-PowerBI-Connection': String(connectionId) },
  });
}

export function listSemanticModels(connectionId, workspaceId) {
  return request(`/powerbi/workspaces/${workspaceId}/semantic-models`, {
    headers: { 'X-PowerBI-Connection': String(connectionId) },
  });
}

export function selectSemanticModel(connectionId, workspaceId, semanticModelId) {
  return request('/powerbi/semantic-models/select', {
    method: 'POST',
    headers: { 'X-PowerBI-Connection': String(connectionId) },
    body: JSON.stringify({
      workspace_id: workspaceId,
      semantic_model_id: semanticModelId,
    }),
  });
}

export function listProjects() {
  return request('/projects');
}

export function createProject(payload) {
  return request('/projects', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getProject(projectId) {
  return request(`/projects/${projectId}`);
}

export function updateProject(projectId, payload) {
  return request(`/projects/${projectId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteProject(projectId) {
  return request(`/projects/${projectId}`, { method: 'DELETE' });
}

export function refreshProjectMetadata(projectId) {
  return request(`/projects/${projectId}/metadata-refresh`, { method: 'POST' });
}

export function getProjectFields(projectId) {
  return request(`/projects/${projectId}/fields`);
}

export function listProjectVisualTemplates() {
  return request('/projects/visual-templates');
}

export function importProjectVisualTemplates(file) {
  const formData = new FormData();
  formData.append('archive', file);
  return request('/projects/visual-templates/import', {
    method: 'POST',
    body: formData,
  });
}

export function validateProject(projectId) {
  return request(`/projects/${projectId}/validate`, { method: 'POST' });
}

export function compileProject(projectId) {
  return request(`/projects/${projectId}/compile`, { method: 'POST' }).then((response) => response.blob());
}

export function createProjectPage(projectId, payload) {
  return request(`/projects/${projectId}/pages`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateProjectPage(projectId, pageId, payload) {
  return request(`/projects/${projectId}/pages/${pageId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteProjectPage(projectId, pageId) {
  return request(`/projects/${projectId}/pages/${pageId}`, { method: 'DELETE' });
}

export function createProjectVisual(projectId, pageId, payload) {
  return request(`/projects/${projectId}/pages/${pageId}/visuals`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateProjectVisual(projectId, pageId, visualId, payload) {
  return request(`/projects/${projectId}/pages/${pageId}/visuals/${visualId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteProjectVisual(projectId, pageId, visualId) {
  return request(`/projects/${projectId}/pages/${pageId}/visuals/${visualId}`, { method: 'DELETE' });
}
