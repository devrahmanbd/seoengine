import axios from 'axios'

const api = axios.create({
  baseURL: '/api/admin/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data)
    return Promise.reject(error)
  }
)

export default api

// Users
export const usersApi = {
  list: (params?: Record<string, any>) => api.get('/users', { params }),
  get: (id: string) => api.get(`/users/${id}`),
  create: (data: any) => api.post('/users', data),
  update: (id: string, data: any) => api.put(`/users/${id}`, data),
  delete: (id: string) => api.delete(`/users/${id}`),
}

// Websites
export const websitesApi = {
  list: (params?: Record<string, any>) => api.get('/websites', { params }),
  get: (id: string) => api.get(`/websites/${id}`),
  delete: (id: string) => api.delete(`/websites/${id}`),
  scan: (id: string, data: any) => api.post(`/websites/${id}/scan`, data),
}

// API Keys
export const apiKeysApi = {
  list: (params?: Record<string, any>) => api.get('/api-keys', { params }),
  get: (id: string) => api.get(`/api-keys/${id}`),
  create: (data: any) => api.post('/api-keys', data),
  delete: (id: string) => api.delete(`/api-keys/${id}`),
}

// Results
export const resultsApi = {
  summary: () => api.get('/results/summary'),
  list: (params?: Record<string, any>) => api.get('/results', { params }),
  issues: (params?: Record<string, any>) => api.get('/results/issues', { params }),
}

// Backend
export const backendApi = {
  status: () => api.get('/backend/status'),
  health: () => api.get('/backend/health'),
  errorLogs: (params?: Record<string, any>) => api.get('/logs/errors', { params }),
  tasks: (params?: Record<string, any>) => api.get('/tasks', { params }),
}

// AI Logs
export const aiLogsApi = {
  list: (params?: Record<string, any>) => api.get('/ai-logs', { params }),
  stats: () => api.get('/ai-logs/stats'),
  agents: () => api.get('/ai-logs/agents'),
}

// Growth
export const growthApi = {
  getState: (websiteId: string) => api.get(`/growth/${websiteId}`),
  compare: (websiteIds: string[]) => api.post('/growth/compare', { website_ids: websiteIds }),
  checkIntervention: (websiteId: string) => api.get(`/growth/${websiteId}/intervention`),
  effectiveActions: (websiteId: string) => api.get(`/growth/${websiteId}/effective-actions`),
  opportunities: (websiteId: string, data: any) => api.post(`/growth/${websiteId}/opportunities`, data),
  schedule: (websiteId: string, data: any) => api.post(`/growth/${websiteId}/schedule`, data),
}