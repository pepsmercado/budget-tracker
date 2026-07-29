import { ref } from 'vue'
import api from '../api'

const token = ref(localStorage.getItem('auth_token') || '')
const isVerified = ref(!!token.value)
const isEnabled = ref(false)
const error = ref('')
const loading = ref(false)

export function useAuth() {
  async function checkStatus() {
    try {
      const { data } = await api.get('/auth/status')
      isEnabled.value = data.enabled
    } catch {
      isEnabled.value = false
    }
  }

  async function verify(pin) {
    loading.value = true
    error.value = ''
    try {
      const { data } = await api.post('/auth/verify', { pin })
      token.value = data.token
      localStorage.setItem('auth_token', data.token)
      isVerified.value = true
    } catch (e) {
      error.value = e.response?.data?.detail || 'Invalid code'
      throw e
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = ''
    isVerified.value = false
    localStorage.removeItem('auth_token')
  }

  return { isVerified, isEnabled, error, loading, checkStatus, verify, logout }
}
