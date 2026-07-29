import { ref } from 'vue'
import api from '../api'

export function useTransfers() {
  const transfers = ref([])
  const loading = ref(false)
  let lastCurrency = null

  async function fetchTransfers(currency) {
    lastCurrency = currency
    loading.value = true
    try {
      const params = {}
      if (currency) params.currency = currency
      const { data } = await api.get('/transfers', { params })
      transfers.value = data
    } finally {
      loading.value = false
    }
  }

  async function createTransfer(payload) {
    try {
      const { data } = await api.post('/transfers', payload)
      await fetchTransfers(lastCurrency)
      return data
    } catch (e) {
      console.warn('createTransfer failed:', e)
      throw e
    }
  }

  async function deleteTransfer(transferId) {
    try {
      await api.delete(`/transfers/${transferId}`)
      await fetchTransfers(lastCurrency)
    } catch (e) {
      console.warn('deleteTransfer failed:', e)
      throw e
    }
  }

  return { transfers, loading, fetchTransfers, createTransfer, deleteTransfer }
}
