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
    try {
      const { data } = await api.post('/recurring', payload)
      await fetchRules(lastCurrency)
      return data
    } catch (e) {
      console.warn('createRule failed:', e)
      throw e
    }
  }

  async function updateRule(ruleId, payload) {
    try {
      const { data } = await api.put(`/recurring/${ruleId}`, payload)
      await fetchRules(lastCurrency)
      return data
    } catch (e) {
      console.warn('updateRule failed:', e)
      throw e
    }
  }

  async function deleteRule(ruleId) {
    try {
      await api.delete(`/recurring/${ruleId}`)
      await fetchRules(lastCurrency)
    } catch (e) {
      console.warn('deleteRule failed:', e)
      throw e
    }
  }

  async function toggleRule(ruleId, active) {
    try {
      const { data } = await api.put(`/recurring/${ruleId}/toggle`, { active })
      await fetchRules(lastCurrency)
      return data
    } catch (e) {
      console.warn('toggleRule failed:', e)
      throw e
    }
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
