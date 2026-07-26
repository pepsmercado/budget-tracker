<script setup>
import { computed, onMounted, onBeforeUnmount, ref, inject, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSummary } from '../composables/useSummary'
import { useExchangeRate } from '../composables/useExchangeRate'
import { useTheme } from '../composables/useTheme'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const { balances, fetchBalances } = useSummary()
const { exchangeRate, lastUpdated, fetchExchangeRate } = useExchangeRate()
const sidebarOpen = inject('sidebarOpen')
const { theme, toggleTheme } = useTheme()
const { isVerified, logout } = useAuth()

const showNetWorthTooltip = ref(false)
const showRateTooltip = ref(false)

function toggleNetWorthTooltip() {
  showNetWorthTooltip.value = !showNetWorthTooltip.value
  showRateTooltip.value = false
}

function toggleRateTooltip() {
  showRateTooltip.value = !showRateTooltip.value
  showNetWorthTooltip.value = false
}

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

const effectiveTheme = computed(() => {
  if (theme.value === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return theme.value
})

onMounted(() => {
  fetchBalances()
  fetchExchangeRate()
  document.addEventListener('click', handleDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
})

function handleDocumentClick(e) {
  const header = e.target.closest('header')
  if (!header) {
    showNetWorthTooltip.value = false
    showRateTooltip.value = false
  }
}

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
  <header class="h-12 bg-white dark:bg-mushroom-900 border-b border-mushroom-200 dark:border-mushroom-700 flex items-center justify-between px-3 sm:px-5 relative">
    <div class="flex items-center gap-3">
      <button @click="sidebarOpen = !sidebarOpen" class="lg:hidden text-mushroom-500 dark:text-mushroom-400 hover:text-mushroom-700 dark:hover:text-mushroom-200 transition-colors">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
      </button>
    </div>
    <div class="flex items-center gap-3 sm:gap-5">
      <button
        @click="toggleTheme"
        class="p-1.5 rounded-lg text-mushroom-400 dark:text-mushroom-500 hover:text-mushroom-700 dark:hover:text-mushroom-200 hover:bg-mushroom-100 dark:hover:bg-mushroom-800 transition-colors"
        :title="effectiveTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
      >
        <svg v-if="effectiveTheme === 'dark'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
        <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
        </svg>
      </button>
      <button
        v-if="isVerified"
        @click="logout"
        class="p-1.5 rounded-lg text-mushroom-400 dark:text-mushroom-500 hover:text-mushroom-700 dark:hover:text-mushroom-200 hover:bg-mushroom-100 dark:hover:bg-mushroom-800 transition-colors"
        title="Lock"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>
        </svg>
      </button>
      <div
        class="relative hidden sm:block"
        @mouseenter="showRateTooltip = true"
        @mouseleave="showRateTooltip = false"
        @click="toggleRateTooltip"
      >
        <span
          class="text-xs text-mushroom-500 dark:text-mushroom-400 cursor-pointer hover:text-kangkong-600 dark:hover:text-kangkong-400 transition-colors"
          @click="openExchangeRateSite"
        >{{ rateDisplay }}</span>

        <div
          v-if="showRateTooltip"
          class="absolute right-0 top-full mt-2 w-48 card-elevated shadow-lg p-3 z-50"
        >
          <div class="text-xs font-medium text-mushroom-700 dark:text-mushroom-300 mb-2">Exchange Rate</div>
          <div class="space-y-1">
            <div class="flex items-center justify-between text-xs">
              <span class="text-mushroom-500 dark:text-mushroom-400">USD → PHP</span>
              <span class="font-medium text-mushroom-800 dark:text-mushroom-200">₱{{ exchangeRate?.toFixed(2) || '—' }}</span>
            </div>
            <div class="flex items-center justify-between text-xs">
              <span class="text-mushroom-500 dark:text-mushroom-400">PHP → USD</span>
              <span class="font-medium text-mushroom-800 dark:text-mushroom-200">{{ phpToUsd }}</span>
            </div>
          </div>
          <div class="mt-2 pt-2 border-t border-mushroom-100 dark:border-mushroom-700 text-[10px] text-mushroom-400 dark:text-mushroom-500">
            Click to view live rate
          </div>
        </div>
      </div>
      <div class="w-px h-4 bg-mushroom-200 dark:bg-mushroom-700"></div>
      <div
        class="relative group"
        @mouseenter="showNetWorthTooltip = true"
        @mouseleave="showNetWorthTooltip = false"
        @click="toggleNetWorthTooltip"
      >
        <div class="flex items-center gap-1.5 cursor-default">
          <span class="text-xs text-mushroom-400 dark:text-mushroom-500">
            {{ currentCurrency === 'USD' ? '🇺🇸' : '🇵🇭' }} Net Worth
          </span>
          <span class="text-sm font-semibold text-kangkong-700 dark:text-mushroom-100">{{ totalNetWorth }}</span>
        </div>

        <div
          v-if="showNetWorthTooltip"
          class="absolute right-0 top-full mt-2 w-72 max-w-[calc(100vw-2rem)] card-elevated shadow-lg p-4 z-50"
        >
          <div class="text-xs font-medium text-mushroom-700 dark:text-mushroom-300 mb-3">
            {{ currentCurrency === 'USD' ? '🇺🇸 US Accounts' : '🇵🇭 Philippine Accounts' }}
          </div>

          <div v-for="b in filteredBalances" :key="b.account_id" class="flex items-center justify-between py-0.5 text-xs">
            <span class="text-mushroom-600 dark:text-mushroom-400">{{ b.account_name }}</span>
            <span class="font-medium text-mushroom-800 dark:text-mushroom-200">{{ formatBal(b.balance, b.currency) }}</span>
          </div>

          <div class="border-t border-mushroom-100 dark:border-mushroom-700 pt-2 mt-2">
            <div class="flex items-center justify-between text-xs">
              <span class="text-mushroom-500 dark:text-mushroom-400">Total ({{ currentCurrency }})</span>
              <span class="font-semibold text-kangkong-700 dark:text-mushroom-100">{{ totalNetWorth }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>
