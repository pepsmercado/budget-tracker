import { ref, computed } from 'vue'
import api from '../api'
import { useToast } from './useToast'

export function useSavingsPlanner() {
  const state = ref(null)
  const loading = ref(false)
  const toast = useToast()

  const linked = computed(() => !!state.value?.planner)
  const linkedAccount = computed(() => state.value?.linked_account || null)
  const savingsAccounts = computed(() => state.value?.savings_accounts || [])
  const balance = computed(() => state.value?.balance ?? 0)
  const unallocated = computed(() => state.value?.unallocated ?? 0)
  const underfunded = computed(() => !!state.value?.underfunded)
  const reserves = computed(() => state.value?.reserves || [])
  const goals = computed(() => state.value?.goals || [])
  const activity = computed(() => state.value?.activity || [])

  async function request(fn, errorMessage) {
    try {
      const { data } = await fn()
      state.value = data
      return data
    } catch (e) {
      toast.error(e.response?.data?.detail || errorMessage)
      throw e
    }
  }

  async function fetchPlanner(currency, limit = 50) {
    loading.value = true
    try {
      const { data } = await api.get(`/savings-planner/${currency}`, { params: { limit } })
      state.value = data
      return data
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load savings planner')
      throw e
    } finally {
      loading.value = false
    }
  }

  function linkPlanner(currency, accountId) {
    return request(() => api.post(`/savings-planner/${currency}/link`, { account_id: accountId }), 'Failed to link account')
  }

  function createReserve(currency, payload) {
    return request(() => api.post(`/savings-planner/${currency}/reserves`, payload), 'Failed to create reserve')
  }

  function updateReserve(currency, id, payload) {
    return request(() => api.put(`/savings-planner/${currency}/reserves/${id}`, payload), 'Failed to update reserve')
  }

  function deleteReserve(currency, id) {
    return request(() => api.delete(`/savings-planner/${currency}/reserves/${id}`), 'Failed to delete reserve')
  }

  function createGoal(currency, payload) {
    return request(() => api.post(`/savings-planner/${currency}/goals`, payload), 'Failed to create goal')
  }

  function updateGoal(currency, id, payload) {
    return request(() => api.put(`/savings-planner/${currency}/goals/${id}`, payload), 'Failed to update goal')
  }

  function deleteGoal(currency, id) {
    return request(() => api.delete(`/savings-planner/${currency}/goals/${id}`), 'Failed to delete goal')
  }

  function convertGoal(currency, id) {
    return request(() => api.post(`/savings-planner/${currency}/goals/${id}/convert`), 'Failed to convert goal')
  }

  function moveMoney(currency, payload) {
    return request(() => api.post(`/savings-planner/${currency}/move`, payload), 'Failed to move money')
  }

  function allocateMoney(currency, allocations) {
    return request(() => api.post(`/savings-planner/${currency}/allocate`, { allocations }), 'Failed to allocate money')
  }

  return {
    state, loading, linked, linkedAccount, savingsAccounts, balance, unallocated,
    underfunded, reserves, goals, activity,
    fetchPlanner, linkPlanner, createReserve, updateReserve, deleteReserve,
    createGoal, updateGoal, deleteGoal, convertGoal, moveMoney, allocateMoney,
  }
}
