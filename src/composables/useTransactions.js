import { ref } from 'vue'
import api from '../api'

export function useTransactions() {
  const transactions = ref([])
  const loading = ref(false)

  async function fetchTransactions(filters = {}) {
    loading.value = true
    try {
      const params = {}
      if (filters.account_id) params.account_id = filters.account_id
      if (filters.type) params.type = filters.type
      if (filters.group) params.group = filters.group
      if (filters.category) params.category = filters.category
      if (filters.start_date) params.start_date = filters.start_date
      if (filters.end_date) params.end_date = filters.end_date
      if (filters.currency) params.currency = filters.currency
      const { data } = await api.get('/transactions', { params })
      transactions.value = data
    } finally {
      loading.value = false
    }
  }

  async function createTransaction(payload) {
    const { data } = await api.post('/transactions', payload)
    transactions.value.unshift(data)
    return data
  }

  async function updateTransaction(id, payload) {
    const { data } = await api.put(`/transactions/${id}`, payload)
    const idx = transactions.value.findIndex(t => t.id === id)
    if (idx !== -1) transactions.value[idx] = data
    return data
  }

  async function deleteTransaction(id) {
    await api.delete(`/transactions/${id}`)
    transactions.value = transactions.value.filter(t => t.id !== id)
  }

  return { transactions, loading, fetchTransactions, createTransaction, updateTransaction, deleteTransaction }
}
