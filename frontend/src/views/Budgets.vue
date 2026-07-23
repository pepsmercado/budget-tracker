<script setup>
import { ref, onMounted, computed } from 'vue'
import { useBudgets } from '../composables/useBudgets'
import { useTransactions } from '../composables/useTransactions'
import BudgetProgressBar from '../components/BudgetProgressBar.vue'

const { budget, fetchBudget, setBudget } = useBudgets()
const { transactions, fetchTransactions } = useTransactions()

const currentMonth = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
})

const totalBudget = ref(0)
const totalSpent = computed(() => {
  return transactions.value
    .filter(t => t.type === 'expense' && t.date.startsWith(currentMonth.value))
    .reduce((sum, t) => sum + t.amount, 0)
})

onMounted(async () => {
  await Promise.all([fetchBudget(currentMonth.value), fetchTransactions()])
  totalBudget.value = budget.value?.total_budget || 0
})

async function saveBudget() {
  await setBudget(currentMonth.value, { total_budget: totalBudget.value, currency: 'PHP' })
}
</script>

<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-extrabold text-charcoal">Budget</h2>

    <div class="card-elevated p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <div class="text-sm text-charcoal-light font-semibold">Total Budget</div>
          <div class="text-2xl font-extrabold text-charcoal">PHP {{ totalBudget.toLocaleString() }}</div>
        </div>
        <div class="flex items-center gap-2">
          <input v-model.number="totalBudget" type="number" class="input-field w-40" />
          <button @click="saveBudget" class="btn-primary">Save</button>
        </div>
      </div>

      <div class="mb-3 flex justify-between text-sm font-semibold">
        <span class="text-charcoal-light">Spent: <span class="text-coral">PHP {{ totalSpent.toLocaleString() }}</span></span>
        <span class="text-charcoal-light">Remaining: <span class="text-sage-dark">PHP {{ Math.max(0, totalBudget - totalSpent).toLocaleString() }}</span></span>
      </div>
      <BudgetProgressBar :spent="totalSpent" :budget="totalBudget" />
    </div>
  </div>
</template>
