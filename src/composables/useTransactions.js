import { ref } from 'vue'
import api from '../api'

export function useTransactions() {
  const transactions = ref([])
  const loading = ref(false)
  let lastFilters = {}

  async function fetchTransactions(filters = {}) {
    lastFilters = filters
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
    try {
      const { data } = await api.post('/transactions', payload)
      await fetchTransactions(lastFilters)
      return data
    } catch (e) {
      console.warn('createTransaction failed:', e)
      throw e
    }
  }

  async function updateTransaction(id, payload) {
    try {
      const { data } = await api.put(`/transactions/${id}`, payload)
      await fetchTransactions(lastFilters)
      return data
    } catch (e) {
      console.warn('updateTransaction failed:', e)
      throw e
    }
  }

  async function deleteTransaction(id) {
    try {
      await api.delete(`/transactions/${id}`)
      await fetchTransactions(lastFilters)
    } catch (e) {
      console.warn('deleteTransaction failed:', e)
      throw e
    }
  }

  return { transactions, loading, fetchTransactions, createTransaction, updateTransaction, deleteTransaction }
}
