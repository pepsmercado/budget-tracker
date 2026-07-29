import { ref } from 'vue'
import api from '../api'
import { useToast } from './useToast'

export function useAccounts() {
  const accounts = ref([])
  const loading = ref(false)
  const toast = useToast()

  async function fetchAccounts() {
    loading.value = true
    try {
      const { data } = await api.get('/accounts')
      accounts.value = data
    } finally {
      loading.value = false
    }
  }

  async function createAccount(payload) {
    try {
      const { data } = await api.post('/accounts', payload)
      await fetchAccounts()
      toast.success('Account created')
      return data
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to create account')
      throw e
    }
  }

  async function updateAccount(id, payload) {
    try {
      const { data } = await api.put(`/accounts/${id}`, payload)
      await fetchAccounts()
      toast.success('Account updated')
      return data
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to update account')
      throw e
    }
  }

  async function deleteAccount(id) {
    try {
      await api.delete(`/accounts/${id}`)
      await fetchAccounts()
      toast.success('Account deleted')
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to delete account')
      throw e
    }
  }

  async function updateAccountGoal(id, goalAmount) {
    try {
      const { data } = await api.put(`/accounts/${id}/goal`, { goal_amount: goalAmount })
      await fetchAccounts()
      toast.success('Goal updated')
      return data
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to update goal')
      throw e
    }
  }

  return { accounts, loading, fetchAccounts, createAccount, updateAccount, deleteAccount, updateAccountGoal }
}
