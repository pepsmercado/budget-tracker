<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useBudgets } from '../composables/useBudgets'
import api from '../api'
import BudgetProgressBar from '../components/BudgetProgressBar.vue'
import { categoryIcons } from '../constants.js'

const props = defineProps({ currency: { type: String, default: 'php' } })

const { budgetSummary, fetchBudgetSummary } = useBudgets()

const currencyParam = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')
const currencySymbol = computed(() => props.currency === 'usd' ? '$' : '₱')
const viewLabel = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')

const now = new Date()
const selectedMonth = ref(localStorage.getItem(`budgets-month-${currencyParam.value}`) || `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const categories = ref([])
const editingCategory = ref(null)
const editValue = ref(0)
const showHidden = ref(false)

const hiddenStorageKey = computed(() => `budgets-hidden-${currencyParam.value}-${selectedMonth.value}`)
const hiddenCategories = ref(new Set(JSON.parse(localStorage.getItem(hiddenStorageKey.value) || '[]')))

function isHidden(catName) {
  return hiddenCategories.value.has(catName)
}

function toggleHide(catName) {
  const next = new Set(hiddenCategories.value)
  if (next.has(catName)) {
    next.delete(catName)
  } else {
    next.add(catName)
  }
  hiddenCategories.value = next
  localStorage.setItem(hiddenStorageKey.value, JSON.stringify([...next]))
}

const hiddenCount = computed(() => {
  if (!budgetSummary.value?.categories) return 0
  return budgetSummary.value.categories.filter(c => hiddenCategories.value.has(c.name)).length
})

const monthLabel = computed(() => {
  const [y, m] = selectedMonth.value.split('-')
  return new Date(parseInt(y), parseInt(m) - 1).toLocaleString('en-US', { month: 'long', year: 'numeric' })
})

const budgetCategories = computed(() => {
  if (!budgetSummary.value?.categories) return []
  return budgetSummary.value.categories.filter(c => showHidden.value ? hiddenCategories.value.has(c.name) : !hiddenCategories.value.has(c.name))
})

const groupedBudgetCategories = computed(() => {
  const groups = {}
  for (const cat of budgetCategories.value) {
    if (!groups[cat.group]) groups[cat.group] = []
    groups[cat.group].push(cat)
  }
  return groups
})

const groupOrder = ['Fixed', 'Essential', 'Lifestyle', 'School', 'Misc', 'Sinking']
const sortedGroupKeys = computed(() => {
  return groupOrder.filter(g => groupedBudgetCategories.value[g])
})

function groupSpent(group) {
  return (groupedBudgetCategories.value[group] || []).reduce((s, c) => s + c.spent, 0)
}

function groupBudget(group) {
  return (groupedBudgetCategories.value[group] || []).reduce((s, c) => s + c.budget, 0)
}

const totalBudget = computed(() => budgetSummary.value?.total_budget || 0)
const totalSpent = computed(() => budgetSummary.value?.total_spent || 0)
const totalRemaining = computed(() => Math.max(0, totalBudget.value - totalSpent.value))
const totalPercent = computed(() => totalBudget.value > 0 ? (totalSpent.value / totalBudget.value) * 100 : 0)

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

function startEdit(cat) {
  editingCategory.value = cat.name
  editValue.value = cat.budget
}

async function saveEdit(cat) {
  const catObj = categories.value.find(c => c.name === cat.name)
  if (catObj) {
    await api.put(`/categories/${catObj.id}/budget`, {
      budget_amount: editValue.value,
      budget_currency: currencyParam.value
    })
  }
  editingCategory.value = null
  await fetchBudgetSummary(selectedMonth.value, currencyParam.value)
}

function cancelEdit() {
  editingCategory.value = null
}

function formatAmount(val) {
  return `${currencySymbol.value}${val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

function formatAmountDecimal(val) {
  return `${currencySymbol.value}${val.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
}

function percent(spent, budget) {
  if (!budget || budget <= 0) return 0
  return Math.min((spent / budget) * 100, 100)
}

async function loadAll() {
  const { data } = await api.get('/categories')
  categories.value = data
  await fetchBudgetSummary(selectedMonth.value, currencyParam.value)
}

onMounted(loadAll)

watch(currencyParam, () => {
  showHidden.value = false
  hiddenCategories.value = new Set(JSON.parse(localStorage.getItem(hiddenStorageKey.value) || '[]'))
  loadAll()
})

watch(selectedMonth, (val) => {
  localStorage.setItem(`budgets-month-${currencyParam.value}`, val)
  showHidden.value = false
  hiddenCategories.value = new Set(JSON.parse(localStorage.getItem(hiddenStorageKey.value) || '[]'))
  fetchBudgetSummary(val, currencyParam.value)
})
</script>

<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-medium text-mushroom-950 dark:text-mushroom-50">{{ viewLabel }} Budgets</h2>
      <div class="flex items-center gap-2">
        <button v-if="hiddenCount > 0" @click="showHidden = !showHidden" class="flex items-center gap-1 px-2 py-1 text-xs rounded-lg transition-colors" :class="showHidden ? 'bg-mushroom-200 dark:bg-mushroom-700 text-mushroom-700 dark:text-mushroom-300' : 'text-mushroom-400 dark:text-mushroom-500 hover:text-mushroom-600 hover:bg-mushroom-100 dark:hover:bg-mushroom-700'">
          <svg v-if="!showHidden" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          {{ showHidden ? 'Showing hidden' : `${hiddenCount} hidden` }}
        </button>
        <button @click="prevMonth" class="p-1.5 rounded-lg hover:bg-mushroom-100 dark:hover:bg-mushroom-700 text-mushroom-500 dark:text-mushroom-400 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <span class="text-sm font-medium text-mushroom-700 dark:text-mushroom-300 min-w-[120px] text-center">{{ monthLabel }}</span>
        <button @click="nextMonth" class="p-1.5 rounded-lg hover:bg-mushroom-100 dark:hover:bg-mushroom-700 text-mushroom-500 dark:text-mushroom-400 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </div>
    </div>

    <div v-if="budgetSummary" class="space-y-5">
      <div class="card-elevated p-6">
        <div class="flex items-center justify-between mb-4">
          <div>
            <div class="text-xs font-medium uppercase tracking-wider text-mushroom-400 dark:text-mushroom-500 mb-1">Total Budget</div>
            <div class="text-3xl font-bold text-mushroom-950 dark:text-mushroom-50">
              {{ formatAmount(totalSpent) }}
              <span class="text-lg font-normal text-mushroom-400 dark:text-mushroom-500">/ {{ formatAmount(totalBudget) }}</span>
            </div>
          </div>
          <div class="text-right">
            <div class="text-xs font-medium uppercase tracking-wider text-mushroom-400 dark:text-mushroom-500 mb-1">Remaining</div>
            <div class="text-xl font-semibold" :class="totalSpent > totalBudget ? 'text-tomato-600 dark:text-tomato-400' : 'text-kangkong-700 dark:text-kangkong-400'">
              {{ formatAmount(totalRemaining) }}
            </div>
            <div class="text-xs mt-0.5" :class="totalSpent > totalBudget ? 'text-tomato-500' : 'text-mushroom-400 dark:text-mushroom-500'">
              {{ totalPercent.toFixed(1) }}% spent
            </div>
          </div>
        </div>
        <BudgetProgressBar :spent="totalSpent" :budget="totalBudget" />
      </div>

      <div v-for="group in sortedGroupKeys" :key="group">
        <div class="flex items-center gap-3 mb-3">
          <h3 class="text-xs font-semibold uppercase tracking-wider text-mushroom-400 dark:text-mushroom-500">{{ group }}</h3>
          <div class="flex-1 h-px bg-mushroom-100 dark:bg-mushroom-800"></div>
          <div class="text-xs text-mushroom-400 dark:text-mushroom-500">
            <span class="font-medium text-mushroom-600 dark:text-mushroom-400">{{ formatAmount(groupSpent(group)) }}</span> / {{ formatAmount(groupBudget(group)) }}
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-5">
          <div v-for="cat in groupedBudgetCategories[group]" :key="cat.name" class="card-elevated p-4 flex flex-col">
            <div class="flex items-start justify-between mb-3">
              <div class="flex items-center gap-2.5">
                <div class="w-9 h-9 rounded-lg bg-mushroom-50 dark:bg-mushroom-800 flex items-center justify-center text-base flex-shrink-0">
                  {{ categoryIcons[cat.name] || '📋' }}
                </div>
                <div>
                  <div class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">{{ cat.name }}</div>
                  <div class="text-[10px] font-medium uppercase tracking-wider text-mushroom-400 dark:text-mushroom-500">{{ cat.group }}</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <button @click="toggleHide(cat.name)" class="text-mushroom-300 dark:text-mushroom-600 hover:text-mushroom-600 transition-colors" :title="showHidden ? 'Unhide' : 'Hide'">
                  <svg v-if="showHidden" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                </button>
                <div class="text-right">
                  <template v-if="editingCategory === cat.name">
                    <input
                      v-model.number="editValue"
                      @keyup.enter="saveEdit(cat)"
                      @keyup.escape="cancelEdit"
                      type="number"
                      step="1"
                      min="0"
                      class="input-field text-sm py-0.5 px-2 w-24 text-right"
                      autofocus
                    />
                  </template>
                  <template v-else>
                    <span
                      @click="startEdit(cat)"
                      class="text-lg font-semibold text-mushroom-950 dark:text-mushroom-50 cursor-pointer hover:text-kangkong-600"
                    >
                      {{ formatAmount(cat.budget) }}
                    </span>
                  </template>
                </div>
              </div>
            </div>
            <div class="mt-auto">
              <BudgetProgressBar :spent="cat.spent" :budget="cat.budget" />
              <div class="flex items-center justify-between mt-2 text-xs">
                <span class="text-mushroom-500 dark:text-mushroom-400">
                  <span class="font-medium text-mushroom-700 dark:text-mushroom-300">{{ formatAmountDecimal(cat.spent) }}</span> spent
                </span>
                <span :class="cat.spent > cat.budget && cat.budget > 0 ? 'text-tomato-600 font-medium' : 'text-kangkong-600'">
                  {{ formatAmount(Math.max(0, cat.budget - cat.spent)) }} left
                </span>
              </div>
              <div class="text-right text-[10px] text-mushroom-400 dark:text-mushroom-500 mt-0.5">
                {{ percent(cat.spent, cat.budget).toFixed(0) }}% used
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-12 text-mushroom-400 dark:text-mushroom-500 text-sm">Loading budget data...</div>
  </div>
</template>
