// Thin wrapper around the ScholarSense API. Every error is normalised to ApiError
// using the backend envelope {"error": {"code", "message", "details"}}.

export const API_BASE = '/api';

export class ApiError extends Error {
  constructor(status, code, message, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function buildQuery(params) {
  if (!params) return '';
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') qs.set(key, String(value));
  });
  const s = qs.toString();
  return s ? `?${s}` : '';
}

async function parseError(res) {
  let body = null;
  try {
    body = await res.json();
  } catch {
    // Non-JSON error (e.g. proxy failure)
  }
  if (body && body.error) {
    return new ApiError(res.status, body.error.code, body.error.message, body.error.details);
  }
  const message =
    res.status === 502 || res.status === 504
      ? 'The ScholarSense API is not reachable. Is the backend running?'
      : `Request failed with status ${res.status}.`;
  return new ApiError(res.status, 'http_error', message);
}

export async function request(path, { method = 'GET', body, form, params, signal } = {}) {
  const init = { method, credentials: 'same-origin', headers: { Accept: 'application/json' }, signal };
  if (form) {
    init.body = form;
  } else if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(`${API_BASE}${path}${buildQuery(params)}`, init);
  } catch (err) {
    if (err && err.name === 'AbortError') throw err;
    throw new ApiError(0, 'network_error', 'Could not reach the ScholarSense API. Check that the backend is running.');
  }
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export const api = {
  health: () => request('/health'),
  upload: (file) => {
    const form = new FormData();
    form.append('file', file);
    return request('/upload', { method: 'POST', form });
  },
  summary: () => request('/dataset/summary'),
  preview: (rows = 20) => request('/dataset/preview', { params: { rows } }),
  checkTarget: (config) => request('/dataset/target', { method: 'POST', body: { ...config, dry_run: true } }),
  confirmTarget: (config) => request('/dataset/target', { method: 'POST', body: { ...config, dry_run: false } }),
  runAnalysis: () => request('/analysis', { method: 'POST' }),
  getAnalysis: () => request('/analysis'),
  train: (params) => request('/models/train', { method: 'POST', body: params || {} }),
  metrics: () => request('/models/metrics'),
  predict: (body) => request('/predictions', { method: 'POST', body }),
  listPredictions: (params) => request('/predictions', { params }),
  setThresholds: (low, high) => request('/predictions/thresholds', { method: 'PUT', body: { low, high } }),
  globalExplanation: (params) => request('/explanations/global', { params }),
  localExplanation: (rowId, params) => request(`/explanations/local/${encodeURIComponent(rowId)}`, { params }),
  interventions: (params) => request('/interventions', { params }),
  intervention: (rowId) => request(`/interventions/${encodeURIComponent(rowId)}`),
  reviewIntervention: (rowId, body) =>
    request(`/interventions/${encodeURIComponent(rowId)}/review`, { method: 'PATCH', body }),
  getMapping: () => request('/interventions/mapping'),
  putMapping: (body) => request('/interventions/mapping', { method: 'PUT', body }),
  deleteSession: () => request('/session', { method: 'DELETE' }),
  exportUrl: (type) => `${API_BASE}/export${buildQuery({ type })}`,
};
