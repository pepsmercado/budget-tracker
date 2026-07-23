import { ref } from 'vue'
import api from '../api'

export function useSummary() {
  const summary = ref(null)
  const balances = ref([])
  const rates = ref(null)
  const loading = ref(false)

  async function fetchSummary(year) {
    loading.value = true
    try {
      const { data } = await api.get(`/summary/${year}`)
      summary.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchBalances() {
    const { data } = await api.get('/balance')
    balances.value = data
  }

  async function fetchRates() {
    const { data } = await api.get('/rates')
    rates.value = data
  }

  return { summary, balances, rates, loading, fetchSummary, fetchBalances, fetchRates }
}
