<script setup>
import { computed, onMounted } from 'vue'
import { useSummary } from '../composables/useSummary'

const { balances, fetchBalances } = useSummary()

onMounted(() => {
  fetchBalances()
})

const totalNetWorth = computed(() => {
  return balances.value.reduce((sum, b) => sum + b.balance_display, 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})
</script>

<template>
  <header class="h-12 bg-white border-b border-mushroom-200 flex items-center justify-between px-5">
    <div></div>
    <div class="flex items-center gap-2">
      <span class="text-xs text-mushroom-400">Net Worth</span>
      <span class="text-sm font-semibold text-kangkong-700">{{ totalNetWorth }}</span>
    </div>
  </header>
</template>
