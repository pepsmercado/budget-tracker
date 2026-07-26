import { ref } from 'vue'
import api from '../api'

export function useBudgets() {
  const loading = ref(false)
  const budgetSummary = ref(null)

  async function fetchBudgetSummary(month, currency) {
    loading.value = true
    try {
      const params = {}
      if (currency) params.currency = currency
      const { data } = await api.get(`/budgets/${month}/summary`, { params })
      budgetSummary.value = data
    } finally {
      loading.value = false
    }
  }

  return { loading, budgetSummary, fetchBudgetSummary }
}
