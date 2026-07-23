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
  <div class="space-y-4">
    <h2 class="text-lg font-medium text-mushroom-950">Budget</h2>

    <div class="card-elevated p-5">
      <div class="flex items-center justify-between mb-4">
        <div>
          <div class="text-xs text-mushroom-400">Total Budget</div>
          <div class="text-xl font-semibold text-mushroom-950">PHP {{ totalBudget.toLocaleString() }}</div>
        </div>
        <div class="flex items-center gap-2">
          <input v-model.number="totalBudget" type="number" class="input-field w-36" />
          <button @click="saveBudget" class="btn-primary">Save</button>
        </div>
      </div>

      <div class="mb-2 flex justify-between text-xs text-mushroom-500">
        <span>Spent: <span class="font-medium text-tomato-600">PHP {{ totalSpent.toLocaleString() }}</span></span>
        <span>Remaining: <span class="font-medium text-kangkong-700">PHP {{ Math.max(0, totalBudget - totalSpent).toLocaleString() }}</span></span>
      </div>
      <BudgetProgressBar :spent="totalSpent" :budget="totalBudget" />
    </div>
  </div>
</template>
