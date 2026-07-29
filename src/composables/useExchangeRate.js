import { ref } from 'vue'
import api from '../api'

const rate = ref(parseFloat(localStorage.getItem('last_known_rate') || '56'))
const loading = ref(false)
const isStale = ref(false)

export function useExchangeRate() {
  async function fetchRate() {
    loading.value = true
    try {
      const { data } = await api.get('/rates')
      if (data && data.PHP_USD) {
        rate.value = data.PHP_USD
        localStorage.setItem('last_known_rate', data.PHP_USD)
        isStale.value = false
      }
    } catch (e) {
      console.warn('Failed to fetch exchange rate, using last known rate:', e)
      isStale.value = true
    } finally {
      loading.value = false
    }
  }

  return { rate, loading, isStale, fetchRate }
}
