import { ref } from 'vue'
import api from '../api'

export function useBudgets() {
  const budget = ref(null)
  const loading = ref(false)

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

  return { budget, loading, fetchBudget, setBudget }
}
