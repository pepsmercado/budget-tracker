import { ref } from 'vue'
import api from '../api'

export function useBudgets() {
  const budget = ref(null)
  const loading = ref(false)
  const budgetSummary = ref(null)

  async function fetchBudget(month) {
    loading.value = true
    try {
      const { data } = await api.get(`/budgets/${month}`)
      budget.value = data
    } finally {
      loading.value = false
    }
  }

  async function setBudget(month, payload) {
    const { data } = await api.put(`/budgets/${month}`, payload)
    budget.value = data
    return data
  }

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

  return { budget, loading, budgetSummary, fetchBudget, setBudget, fetchBudgetSummary }
}
