import { ref } from 'vue'
import api from '../api'

export function useRecurring() {
  const rules = ref([])
  const loading = ref(false)
  const runResult = ref(null)
  let lastCurrency = null

  async function fetchRules(currency) {
    lastCurrency = currency
    loading.value = true
    try {
      const params = {}
      if (currency) params.currency = currency
      const { data } = await api.get('/recurring', { params })
      rules.value = data
    } finally {
      loading.value = false
    }
  }

  async function createRule(payload) {
    const { data } = await api.post('/recurring', payload)
    await fetchRules(lastCurrency)
    return data
  }

  async function updateRule(ruleId, payload) {
    const { data } = await api.put(`/recurring/${ruleId}`, payload)
    await fetchRules(lastCurrency)
    return data
  }

  async function deleteRule(ruleId) {
    await api.delete(`/recurring/${ruleId}`)
    await fetchRules(lastCurrency)
  }

  async function toggleRule(ruleId, active) {
    const { data } = await api.put(`/recurring/${ruleId}/toggle`, { active })
    await fetchRules(lastCurrency)
    return data
  }

  async function runNow(currency) {
    loading.value = true
    try {
      const params = {}
      if (currency) params.currency = currency
      const { data } = await api.post('/recurring/run', null, { params })
      runResult.value = data
      rules.value = data.rules
      return data
    } finally {
      loading.value = false
    }
  }

  return { rules, loading, runResult, fetchRules, createRule, updateRule, deleteRule, toggleRule, runNow }
}
