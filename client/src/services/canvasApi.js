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
      } catch (_readError) {
        // keep default detail
      }
    }
    throw new Error(detail);
  }

  return response;
}

export async function listVisualTemplates() {
  return request('/visual-templates').then((response) => response.json());
}

export async function importVisualTemplates(file) {
  const formData = new FormData();
  formData.append('archive', file);
  return request('/visual-templates/import', {
    method: 'POST',
    body: formData,
  }).then((response) => response.json());
}

export async function listCanvasReports() {
  return request('/canvas-reports').then((response) => response.json());
}

export async function createCanvasReport(payload) {
  return request('/canvas-reports', {
    method: 'POST',
    body: JSON.stringify(payload),
  }).then((response) => response.json());
}

export async function getCanvasReport(reportId) {
  return request(`/canvas-reports/${reportId}`).then((response) => response.json());
}

export async function updateCanvasReport(reportId, payload) {
  return request(`/canvas-reports/${reportId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  }).then((response) => response.json());
}

export async function deleteCanvasReport(reportId) {
  return request(`/canvas-reports/${reportId}`, {
    method: 'DELETE',
  }).then((response) => response.json());
}

export async function getPages(reportId) {
  return request(`/canvas-reports/${reportId}/pages`).then((response) => response.json());
}

export async function createPage(reportId, payload) {
  return request(`/canvas-reports/${reportId}/pages`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }).then((response) => response.json());
}

export async function updatePage(reportId, pageId, payload) {
  return request(`/canvas-reports/${reportId}/pages/${pageId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  }).then((response) => response.json());
}

export async function deletePage(reportId, pageId) {
  return request(`/canvas-reports/${reportId}/pages/${pageId}`, {
    method: 'DELETE',
  }).then((response) => response.json());
}

export async function getVisuals(reportId, pageId) {
  return request(`/canvas-reports/${reportId}/pages/${pageId}/visuals`).then((response) => response.json());
}

export async function createVisual(reportId, pageId, payload) {
  return request(`/canvas-reports/${reportId}/pages/${pageId}/visuals`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }).then((response) => response.json());
}

export async function updateVisual(reportId, pageId, visualId, payload) {
  return request(`/canvas-reports/${reportId}/pages/${pageId}/visuals/${visualId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  }).then((response) => response.json());
}

export async function deleteVisual(reportId, pageId, visualId) {
  return request(`/canvas-reports/${reportId}/pages/${pageId}/visuals/${visualId}`, {
    method: 'DELETE',
  }).then((response) => response.json());
}

export async function getFields(reportId) {
  return request(`/canvas-reports/${reportId}/fields`).then((response) => response.json());
}

export async function validateReport(reportId) {
  return request(`/canvas-reports/${reportId}/validate`, {
    method: 'POST',
  }).then((response) => response.json());
}

export async function compileReport(reportId) {
  return request(`/canvas-reports/${reportId}/compile`, {
    method: 'POST',
  }).then((response) => response.blob());
}

export async function listSemanticModels() {
  return request('/semantic-models').then((response) => response.json());
}

export async function importSemanticModel(file, modelName) {
  const formData = new FormData();
  formData.append('archive', file);
  if (modelName) {
    formData.append('model_name', modelName);
  }
  return request('/semantic-models/import', {
    method: 'POST',
    body: formData,
  }).then((response) => response.json());
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
