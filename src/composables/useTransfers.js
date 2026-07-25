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
    const { data } = await api.post('/transfers', payload)
    await fetchTransfers(lastCurrency)
    return data
  }

  async function deleteTransfer(transferId) {
    await api.delete(`/transfers/${transferId}`)
    await fetchTransfers(lastCurrency)
  }

  return { transfers, loading, fetchTransfers, createTransfer, deleteTransfer }
}
