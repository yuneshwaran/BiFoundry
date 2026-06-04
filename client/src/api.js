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
      detail = payload.detail || payload.message || detail;
    } catch (error) {
      try {
        detail = await response.text();
      } catch (readError) {
        // Keep the default error message when the response body cannot be read.
      }
    }
    throw new Error(detail);
  }

  return response;
}

export async function listSemanticModels() {
  const response = await request('/semantic-models');
  return response.json();
}

export async function importSemanticModel(file, modelName) {
  const formData = new FormData();
  formData.append('archive', file);
  if (modelName) {
    formData.append('model_name', modelName);
  }
  const response = await request('/semantic-models/import', {
    method: 'POST',
    body: formData,
  });
  return response.json();
}

export async function deleteSemanticModel(modelId) {
  const response = await request(`/semantic-models/${modelId}`, {
    method: 'DELETE',
  });
  return response.json();
}

export async function listCanvasReports() {
  const response = await request('/canvas/reports');
  return response.json();
}

export async function listVisualTemplates() {
  const response = await request('/canvas/visual-templates');
  return response.json();
}

export async function createCanvasReport(payload) {
  const response = await request('/canvas/reports', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function getCanvasReport(reportId) {
  const response = await request(`/canvas/reports/${reportId}`);
  return response.json();
}

export async function snapshotCanvasReport(reportId, payload) {
  const response = await request(`/canvas/reports/${reportId}/snapshot`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function updateCanvasReport(reportId, payload) {
  const response = await request(`/canvas/reports/${reportId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function deleteCanvasReport(reportId) {
  const response = await request(`/canvas/reports/${reportId}`, {
    method: 'DELETE',
  });
  return response.json();
}

export async function createCanvasPage(reportId, payload) {
  const response = await request(`/canvas/reports/${reportId}/pages`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function updateCanvasPage(pageId, payload) {
  const response = await request(`/canvas/pages/${pageId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function deleteCanvasPage(pageId) {
  const response = await request(`/canvas/pages/${pageId}`, {
    method: 'DELETE',
  });
  return response.json();
}

export async function createCanvasVisual(pageId, payload) {
  const response = await request(`/canvas/pages/${pageId}/visuals`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function updateCanvasVisual(visualId, payload) {
  const response = await request(`/canvas/visuals/${visualId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function deleteCanvasVisual(visualId) {
  const response = await request(`/canvas/visuals/${visualId}`, {
    method: 'DELETE',
  });
  return response.json();
}

export async function getSourceFields(modelId) {
  const response = await request(`/semantic-models/${modelId}/fields`);
  return response.json();
}

export async function compileCanvasReport(reportId) {
  const response = await request(`/canvas/reports/${reportId}/compile`, {
    method: 'POST',
  });
  return response.blob();
}
