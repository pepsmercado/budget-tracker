import { ref } from 'vue'
import api from '../api'

export function useRecurring() {
  const rules = ref([])
  const loading = ref(false)
  const runResult = ref(null)

  async function fetchRules(currency) {
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
    rules.value.push(data)
    return data
  }

  async function updateRule(ruleId, payload) {
    const { data } = await api.put(`/recurring/${ruleId}`, payload)
    const idx = rules.value.findIndex(r => r.id === ruleId)
    if (idx >= 0) rules.value[idx] = data
    return data
  }

  async function deleteRule(ruleId) {
    await api.delete(`/recurring/${ruleId}`)
    rules.value = rules.value.filter(r => r.id !== ruleId)
  }

  async function toggleRule(ruleId, active) {
    const { data } = await api.put(`/recurring/${ruleId}/toggle`, { active })
    const idx = rules.value.findIndex(r => r.id === ruleId)
    if (idx >= 0) rules.value[idx] = data
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
