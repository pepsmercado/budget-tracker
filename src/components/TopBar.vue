<script setup>
import { computed, onMounted, ref, inject, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSummary } from '../composables/useSummary'
import { useExchangeRate } from '../composables/useExchangeRate'

const route = useRoute()
const { balances, fetchBalances } = useSummary()
const { exchangeRate, lastUpdated, fetchExchangeRate } = useExchangeRate()
const sidebarOpen = inject('sidebarOpen')

const showNetWorthTooltip = ref(false)
const showRateTooltip = ref(false)

const currentCurrency = computed(() => {
  if (route.path.startsWith('/usd')) return 'USD'
  return 'PHP'
})

const currencySymbol = computed(() => currentCurrency.value === 'USD' ? '$' : '₱')

const filteredBalances = computed(() => {
  return balances.value.filter(b => b.currency === currentCurrency.value)
})

const totalNetWorth = computed(() => {
  const total = filteredBalances.value.reduce((sum, b) => sum + b.balance, 0)
  return `${currencySymbol.value}${total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
})

const rateDisplay = computed(() => {
  if (!exchangeRate.value) return '—'
  return `1 USD = ₱${exchangeRate.value.toFixed(2)}`
})

const phpToUsd = computed(() => {
  if (!exchangeRate.value) return '—'
  return `1 PHP = $${(1 / exchangeRate.value).toFixed(4)}`
})

onMounted(() => {
  fetchBalances()
  fetchExchangeRate()
})

watch(() => route.path, () => {
  fetchBalances()
})

function openExchangeRateSite() {
  window.open('https://www.x-rates.com/calculator/?from=USD&to=PHP&amount=1', '_blank')
}

function formatBal(val, currency) {
  if (currency === 'USD') return `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  return `₱${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
</script>

<template>
  <header class="h-12 bg-white border-b border-mushroom-200 flex items-center justify-between px-3 sm:px-5 relative">
    <div class="flex items-center gap-3">
      <button @click="sidebarOpen = !sidebarOpen" class="lg:hidden text-mushroom-500 hover:text-mushroom-700 transition-colors">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
      </button>
    </div>
    <div class="flex items-center gap-3 sm:gap-5">
      <div
        class="relative hidden sm:block"
        @mouseenter="showRateTooltip = true"
        @mouseleave="showRateTooltip = false"
      >
        <span
          class="text-xs text-mushroom-500 cursor-pointer hover:text-kangkong-600 transition-colors"
          @click="openExchangeRateSite"
        >{{ rateDisplay }}</span>

        <div
          v-if="showRateTooltip"
          class="absolute right-0 top-full mt-2 w-48 card-elevated shadow-lg p-3 z-50"
        >
          <div class="text-xs font-medium text-mushroom-700 mb-2">Exchange Rate</div>
          <div class="space-y-1">
            <div class="flex items-center justify-between text-xs">
              <span class="text-mushroom-500">USD → PHP</span>
              <span class="font-medium text-mushroom-800">₱{{ exchangeRate?.toFixed(2) || '—' }}</span>
            </div>
            <div class="flex items-center justify-between text-xs">
              <span class="text-mushroom-500">PHP → USD</span>
              <span class="font-medium text-mushroom-800">{{ phpToUsd }}</span>
            </div>
          </div>
          <div class="mt-2 pt-2 border-t border-mushroom-100 text-[10px] text-mushroom-400">
            Click to view live rate
          </div>
        </div>
      </div>
      <div class="w-px h-4 bg-mushroom-200"></div>
      <div
        class="relative group"
        @mouseenter="showNetWorthTooltip = true"
        @mouseleave="showNetWorthTooltip = false"
      >
        <div class="flex items-center gap-1.5 cursor-default">
          <span class="text-xs text-mushroom-400">
            {{ currentCurrency === 'USD' ? '🇺🇸' : '🇵🇭' }} Net Worth
          </span>
          <span class="text-sm font-semibold" :class="currentCurrency === 'USD' ? 'text-kangkong-700' : 'text-kangkong-700'">{{ totalNetWorth }}</span>
        </div>

        <div
          v-if="showNetWorthTooltip"
          class="absolute right-0 top-full mt-2 w-72 card-elevated shadow-lg p-4 z-50"
        >
          <div class="text-xs font-medium text-mushroom-700 mb-3">
            {{ currentCurrency === 'USD' ? '🇺🇸 US Accounts' : '🇵🇭 Philippine Accounts' }}
          </div>

          <div v-for="b in filteredBalances" :key="b.account_id" class="flex items-center justify-between py-0.5 text-xs">
            <span class="text-mushroom-600">{{ b.account_name }}</span>
            <span class="font-medium text-mushroom-800">{{ formatBal(b.balance, b.currency) }}</span>
          </div>

          <div class="border-t border-mushroom-100 pt-2 mt-2">
            <div class="flex items-center justify-between text-xs">
              <span class="text-mushroom-500">Total ({{ currentCurrency }})</span>
              <span class="font-semibold text-kangkong-700">{{ totalNetWorth }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>
