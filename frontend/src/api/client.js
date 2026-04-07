import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// ─── Requests ────────────────────────────────────────────────────────────────
export const ingestRequest = (features, true_label = null) =>
  api.post('/ingest', { features, true_label }).then(r => r.data)

export const fetchRequests = (limit = 50, offset = 0) =>
  api.get('/requests', { params: { limit, offset } }).then(r => r.data)

// ─── Evaluation ──────────────────────────────────────────────────────────────
export const fetchEvaluation = (window_hours = 24) =>
  api.get('/evaluate', { params: { window_hours } }).then(r => r.data)

export const evaluateModels = (window_hours = 24) =>
  api.post('/evaluate-models', {}, { params: { window_hours } }).then(r => r.data)

export const uploadModelV2 = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/models/v2/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}
export const fetchMetricsHistory = (limit = 100) =>
  api.get('/metrics/history', { params: { limit } }).then(r => r.data)

// ─── Errors ──────────────────────────────────────────────────────────────────
export const fetchErrors = (limit = 50) =>
  api.get('/errors', { params: { limit } }).then(r => r.data)

// ─── Health ──────────────────────────────────────────────────────────────────
export const fetchHealth = () =>
  api.get('/health').then(r => r.data)

export default api
