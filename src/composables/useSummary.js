import { ref } from 'vue'
import api from '../api'

export function useSummary() {
  const summary = ref(null)
  const balances = ref([])
  const loading = ref(false)

  async function fetchSummary(year, currency) {
    loading.value = true
    try {
      const params = {}
      if (currency) params.currency = currency
      const { data } = await api.get(`/summary/${year}`, { params })
      summary.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchBalances(currency) {
    try {
      const params = {}
      if (currency) params.currency = currency
      const { data } = await api.get('/balance', { params })
      balances.value = data
    } catch (e) {
      console.warn('fetchBalances failed:', e)
    }
  }

  return { summary, balances, loading, fetchSummary, fetchBalances }
}
