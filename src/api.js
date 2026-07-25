import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  // Only attach token if ACCESS_PIN is configured (i.e., deployed)
  // On localhost without ACCESS_PIN, server returns auth.enabled=false
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Clear stale token if auth is disabled
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && error.config?.url?.includes('/auth/')) {
      localStorage.removeItem('auth_token')
    }
    return Promise.reject(error)
  }
)

export default api
