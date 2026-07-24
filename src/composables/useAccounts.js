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
    const { data } = await api.post('/accounts', payload)
    accounts.value.push(data)
    toast.success('Account created')
    return data
  }

  async function updateAccount(id, payload) {
    const { data } = await api.put(`/accounts/${id}`, payload)
    const idx = accounts.value.findIndex(a => a.id === id)
    if (idx !== -1) accounts.value[idx] = data
    toast.success('Account updated')
    return data
  }

  async function deleteAccount(id) {
    await api.delete(`/accounts/${id}`)
    accounts.value = accounts.value.filter(a => a.id !== id)
    toast.success('Account deleted')
  }

  async function updateAccountGoal(id, goalAmount) {
    const { data } = await api.put(`/accounts/${id}/goal`, { goal_amount: goalAmount })
    const idx = accounts.value.findIndex(a => a.id === id)
    if (idx !== -1) accounts.value[idx] = data
    toast.success('Goal updated')
    return data
  }

  return { accounts, loading, fetchAccounts, createAccount, updateAccount, deleteAccount, updateAccountGoal }
}
