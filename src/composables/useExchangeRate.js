import { ref, readonly } from 'vue'
import api from '../api'

const exchangeRate = ref(56)
const lastUpdated = ref(null)

async function fetchExchangeRate() {
  try {
    const { data } = await api.get('/rates')
    if (data.rates?.PHP) {
      exchangeRate.value = data.rates.PHP
      lastUpdated.value = new Date()
    }
  } catch {
    // keep default
  }
}

export function useExchangeRate() {
  return {
    exchangeRate: readonly(exchangeRate),
    lastUpdated: readonly(lastUpdated),
    fetchExchangeRate
  }
}
