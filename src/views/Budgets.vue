<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useBudgets } from '../composables/useBudgets'
import { useAccounts } from '../composables/useAccounts'
import api from '../api'
import BudgetProgressBar from '../components/BudgetProgressBar.vue'

const { budgetSummary, fetchBudgetSummary, fetchBudget, setBudget } = useBudgets()
const { accounts, fetchAccounts } = useAccounts()

const now = new Date()
const selectedMonth = ref(localStorage.getItem('budgets-month') || `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const categories = ref([])
const editingCategory = ref(null)
const editValue = ref(0)
const collapsedGroups = ref({})
const loadingCatBudget = ref(null)

const monthLabel = computed(() => {
  const [y, m] = selectedMonth.value.split('-')
  return new Date(parseInt(y), parseInt(m) - 1).toLocaleString('en-US', { month: 'long', year: 'numeric' })
})

const groupedCategories = computed(() => {
  if (!budgetSummary.value?.categories) return {}
  const groups = {}
  for (const cat of budgetSummary.value.categories) {
    if (!groups[cat.group]) groups[cat.group] = []
    groups[cat.group].push(cat)
  }
  return groups
})

const groupOrder = ['Fixed', 'Essential', 'Lifestyle', 'School', 'Misc', 'Sinking']
const sortedGroups = computed(() => {
  return groupOrder.filter(g => groupedCategories.value[g])
})

function groupSpent(group) {
  return (groupedCategories.value[group] || []).reduce((s, c) => s + c.spent, 0)
}

function groupBudget(group) {
  return (groupedCategories.value[group] || []).reduce((s, c) => s + c.budget, 0)
}

function prevMonth() {
  const [y, m] = selectedMonth.value.split('-').map(Number)
  const d = new Date(y, m - 2, 1)
  selectedMonth.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function nextMonth() {
  const [y, m] = selectedMonth.value.split('-').map(Number)
  const d = new Date(y, m, 1)
  selectedMonth.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function toggleGroup(group) {
  collapsedGroups.value[group] = !collapsedGroups.value[group]
}

function startEdit(cat) {
  editingCategory.value = cat.name
  editValue.value = cat.budget
}

async function saveEdit(cat) {
  loadingCatBudget.value = cat.name
  const catObj = categories.value.find(c => c.name === cat.name)
  if (catObj) {
    await api.put(`/categories/${catObj.id}/budget`, {
      budget_amount: editValue.value,
      budget_currency: cat.currency || 'PHP'
    })
  }
  editingCategory.value = null
  await fetchBudgetSummary(selectedMonth.value)
  loadingCatBudget.value = null
}

function cancelEdit() {
  editingCategory.value = null
}

function formatAmount(val, currency) {
  if (currency === 'USD') return `$${val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
  return `₱${val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

onMounted(async () => {
  const { data } = await api.get('/categories')
  categories.value = data
  await fetchBudgetSummary(selectedMonth.value)
})

watch(selectedMonth, (val) => {
  localStorage.setItem('budgets-month', val)
  fetchBudgetSummary(val)
})
</script>

<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-medium text-mushroom-950">Budget</h2>
      <div class="flex items-center gap-2">
        <button @click="prevMonth" class="p-1.5 rounded-lg hover:bg-mushroom-100 text-mushroom-500 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <span class="text-sm font-medium text-mushroom-700 min-w-[120px] text-center">{{ monthLabel }}</span>
        <button @click="nextMonth" class="p-1.5 rounded-lg hover:bg-mushroom-100 text-mushroom-500 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </div>
    </div>

    <div v-if="budgetSummary" class="card-elevated p-5">
      <div class="flex items-center justify-between mb-3">
        <div>
          <div class="text-xs text-mushroom-400">Total Budget</div>
          <div class="text-2xl font-semibold text-mushroom-950">
            {{ formatAmount(budgetSummary.total_spent, 'PHP') }}
            <span class="text-sm font-normal text-mushroom-400">/ {{ formatAmount(budgetSummary.total_budget, 'PHP') }}</span>
          </div>
        </div>
        <div class="text-right">
          <div class="text-xs text-mushroom-400">Remaining</div>
          <div class="text-sm font-semibold" :class="budgetSummary.total_spent > budgetSummary.total_budget ? 'text-tomato-600' : 'text-kangkong-700'">
            {{ formatAmount(Math.max(0, budgetSummary.total_budget - budgetSummary.total_spent), 'PHP') }}
          </div>
        </div>
      </div>
      <BudgetProgressBar :spent="budgetSummary.total_spent" :budget="budgetSummary.total_budget" />
      <div class="mt-2 text-right text-xs text-mushroom-400">
        {{ budgetSummary.total_budget > 0 ? ((budgetSummary.total_spent / budgetSummary.total_budget) * 100).toFixed(1) : 0 }}% spent
      </div>
    </div>

    <div v-if="budgetSummary" class="space-y-3">
      <div v-for="group in sortedGroups" :key="group" class="card-elevated overflow-hidden">
        <button
          @click="toggleGroup(group)"
          class="w-full flex items-center justify-between px-5 py-3 hover:bg-mushroom-50 transition-colors"
        >
          <div class="flex items-center gap-2">
            <svg
              width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              class="text-mushroom-400 transition-transform duration-200"
              :class="collapsedGroups[group] ? '' : 'rotate-90'"
            ><path d="M9 18l6-6-6-6"/></svg>
            <span class="text-sm font-medium text-mushroom-800">{{ group }}</span>
          </div>
          <div class="flex items-center gap-3 text-xs">
            <span class="text-mushroom-500">{{ formatAmount(groupSpent(group), 'PHP') }} / {{ formatAmount(groupBudget(group), 'PHP') }}</span>
            <BudgetProgressBar :spent="groupSpent(group)" :budget="groupBudget(group)" class="w-20" />
          </div>
        </button>

        <div v-if="!collapsedGroups[group]" class="border-t border-mushroom-100">
          <div v-for="cat in groupedCategories[group]" :key="cat.name" class="px-5 py-3 border-b border-mushroom-50 last:border-b-0">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm text-mushroom-700">{{ cat.name }}</span>
              <div class="flex items-center gap-2">
                <template v-if="editingCategory === cat.name">
                  <input
                    v-model.number="editValue"
                    @keyup.enter="saveEdit(cat)"
                    @keyup.escape="cancelEdit"
                    @blur="saveEdit(cat)"
                    type="number"
                    step="1"
                    min="0"
                    class="input-field text-sm py-0.5 px-2 w-24"
                    autofocus
                  />
                </template>
                <template v-else>
                  <span
                    @click="startEdit(cat)"
                    class="cursor-pointer hover:text-kangkong-600 text-sm font-medium text-mushroom-700"
                  >
                    {{ formatAmount(cat.budget, cat.currency) }}
                  </span>
                </template>
              </div>
            </div>
            <BudgetProgressBar :spent="cat.spent" :budget="cat.budget" />
            <div class="mt-1 text-xs text-mushroom-400 text-right">
              {{ formatAmount(cat.spent, cat.currency) }} / {{ formatAmount(cat.budget, cat.currency) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-12 text-mushroom-400 text-sm">Loading budget data...</div>
  </div>
</template>
