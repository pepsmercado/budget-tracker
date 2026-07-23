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
  <header class="h-16 bg-white border-b border-cream-dark flex items-center justify-between px-6">
    <div></div>
    <div class="flex items-center gap-3">
      <div class="text-sm text-charcoal-light">Net Worth</div>
      <div class="bg-sage/10 text-sage-dark px-4 py-1.5 rounded-full font-extrabold text-sm">
        {{ totalNetWorth }}
      </div>
    </div>
  </header>
</template>
