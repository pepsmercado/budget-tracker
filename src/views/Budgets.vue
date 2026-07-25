<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useBudgets } from '../composables/useBudgets'
import api from '../api'
import BudgetProgressBar from '../components/BudgetProgressBar.vue'
import Skeleton from '../components/Skeleton.vue'
import { categoryIcons } from '../constants.js'
import { useToast } from '../composables/useToast.js'

const props = defineProps({ currency: { type: String, default: 'php' } })

const { budgetSummary, loading, fetchBudgetSummary } = useBudgets()
const toast = useToast()

const currencyParam = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')
const currencySymbol = computed(() => props.currency === 'usd' ? '$' : '₱')
const viewLabel = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')

const now = new Date()
const selectedMonth = ref(localStorage.getItem(`budgets-month-${currencyParam.value}`) || `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const categories = ref([])
const categoriesLoading = ref(true)
const editingCategory = ref(null)
const editValue = ref(0)
const showHidden = ref(false)
const monthlyOverrides = ref({})
const showTemplateEditor = ref(false)
const templateEditValues = ref({})
const templateEditorLoading = ref(false)
const templateEditorSaving = ref(false)

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
  try {
    await api.put(`/monthly-budgets/${selectedMonth.value}`, {
      category: cat.name,
      budget: editValue.value,
      currency: currencyParam.value,
    })
    editingCategory.value = null
    await fetchBudgetSummary(selectedMonth.value, currencyParam.value)
    await fetchMonthlyOverrides()
  } catch (e) {
    console.error('Failed to save budget:', e)
    toast.error('Failed to save budget: ' + (e.response?.data?.detail || e.message))
  }
}

async function fetchMonthlyOverrides() {
  const { data } = await api.get(`/monthly-budgets/${selectedMonth.value}`, { params: { currency: currencyParam.value } })
  monthlyOverrides.value = data
}

async function saveAsTemplate() {
  try {
    const overrides = budgetSummary.value.categories.map(c => ({
      category: c.name,
      budget: c.budget,
      currency: currencyParam.value,
    }))
    await api.post(`/monthly-budgets/${selectedMonth.value}/bulk`, { overrides })
    await fetchBudgetSummary(selectedMonth.value, currencyParam.value)
    await fetchMonthlyOverrides()
  } catch (e) {
    console.error('Failed to save template:', e)
    toast.error('Failed to save template: ' + (e.response?.data?.detail || e.message))
  }
}

async function resetToTemplate() {
  try {
    await api.delete(`/monthly-budgets/${selectedMonth.value}`, { params: { currency: currencyParam.value } })
    await fetchBudgetSummary(selectedMonth.value, currencyParam.value)
    await fetchMonthlyOverrides()
  } catch (e) {
    console.error('Failed to reset template:', e)
    toast.error('Failed to reset template: ' + (e.response?.data?.detail || e.message))
  }
}

async function openTemplateEditor() {
  templateEditValues.value = {}
  templateEditorLoading.value = true
  try {
    if (!categories.value || categories.value.length === 0) {
      await loadAll()
    }
    const expenseCategories = categories.value?.filter(c => c.type === 'expense') || []
    for (const cat of expenseCategories) {
      templateEditValues.value[cat.name] = cat.budget_amount || 0
    }
    showTemplateEditor.value = true
  } catch (e) {
    console.error('Failed to load template editor:', e)
    toast.error('Failed to load template editor: ' + (e.response?.data?.detail || e.message))
  } finally {
    templateEditorLoading.value = false
  }
}

async function saveTemplateEditor() {
  templateEditorSaving.value = true
  try {
    const updates = Object.entries(templateEditValues.value).map(([name, budget]) => ({
      name,
      budget_amount: budget,
    }))
    await api.put('/categories/bulk-budget', { updates })
    showTemplateEditor.value = false
    await fetchBudgetSummary(selectedMonth.value, currencyParam.value)
    await fetchMonthlyOverrides()
    toast.success('Template saved')
  } catch (e) {
    console.error('Failed to save template:', e)
    toast.error('Failed to save template: ' + (e.response?.data?.detail || e.message))
  } finally {
    templateEditorSaving.value = false
  }
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
  categoriesLoading.value = true
  try {
    const { data } = await api.get('/categories')
    categories.value = data
  } finally {
    categoriesLoading.value = false
  }
  await fetchBudgetSummary(selectedMonth.value, currencyParam.value)
  await fetchMonthlyOverrides()
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
  fetchMonthlyOverrides()
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
        <button @click="openTemplateEditor" :disabled="categoriesLoading" class="p-1.5 rounded-lg hover:bg-mushroom-100 dark:hover:bg-mushroom-700 text-mushroom-500 dark:text-mushroom-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed" title="Edit Template">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        </button>
        <button v-if="Object.keys(monthlyOverrides).length > 0" @click="resetToTemplate" class="p-1.5 rounded-lg hover:bg-mushroom-100 dark:hover:bg-mushroom-700 text-mushroom-500 dark:text-mushroom-400 transition-colors" title="Reset to Template">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 109-9 9.75 9.75 0 00-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
        </button>
        <button @click="prevMonth" class="p-1.5 rounded-lg hover:bg-mushroom-100 dark:hover:bg-mushroom-700 text-mushroom-500 dark:text-mushroom-400 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <span class="text-sm font-medium text-mushroom-700 dark:text-mushroom-300 min-w-[120px] text-center">{{ selectedMonth }}</span>
        <button @click="nextMonth" class="p-1.5 rounded-lg hover:bg-mushroom-100 dark:hover:bg-mushroom-700 text-mushroom-500 dark:text-mushroom-400 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </div>
    </div>

    <div v-if="loading" class="space-y-6">
      <div v-for="g in 2" :key="g">
        <Skeleton width="80px" height="10px" class="mb-3" />
        <div class="space-y-3">
          <div v-for="c in 2" :key="c" class="card-elevated p-4 border-l-4 border-l-mushroom-200 dark:border-l-mushroom-700">
            <div class="flex items-center justify-between mb-2">
              <div class="space-y-1.5">
                <div class="flex items-center gap-2">
                  <Skeleton width="40px" height="16px" rounded="rounded-full" />
                  <Skeleton width="100px" height="14px" />
                </div>
                <Skeleton width="80px" height="10px" />
              </div>
              <Skeleton width="100px" height="20px" />
            </div>
            <Skeleton width="100%" height="8px" rounded="rounded" />
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="budgetSummary" class="space-y-5">
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

  <!-- Template Editor Modal -->
  <div v-if="showTemplateEditor" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="showTemplateEditor = false">
    <div class="w-full max-w-5xl max-h-[80vh] overflow-y-auto card-elevated rounded-xl p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-medium text-mushroom-950 dark:text-mushroom-50">Edit Budget Template ({{ viewLabel }})</h3>
        <button @click="showTemplateEditor = false" class="p-1 text-mushroom-400 hover:text-mushroom-600">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <p class="text-xs text-mushroom-400 dark:text-mushroom-500 mb-4">Changes here become the default for new months. Monthly overrides are unaffected.</p>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 gap-3 max-h-[60vh] overflow-y-auto">
        <template v-if="templateEditorLoading || (!categories || categories.length === 0)">
          <div v-for="g in 6" :key="g" class="flex items-center gap-2 p-2 bg-mushroom-50 dark:bg-mushroom-800 rounded-lg flex-nowrap">
            <Skeleton width="28px" height="28px" rounded="rounded-lg" />
            <div class="flex-1 space-y-1.5">
              <Skeleton width="120px" height="16px" />
              <Skeleton width="80px" height="10px" />
            </div>
            <Skeleton width="48px" height="28px" />
          </div>
        </template>
        <template v-else>
          <div v-for="cat in (categories || []).filter(c => c.type === 'expense')" :key="cat.name" class="flex items-center gap-2 p-2 bg-mushroom-50 dark:bg-mushroom-800 rounded-lg overflow-hidden">
            <div class="w-7 h-7 rounded-lg bg-mushroom-100 dark:bg-mushroom-700 flex items-center justify-center text-sm flex-shrink-0">
              {{ categoryIcons[cat.name] || '📋' }}
            </div>
            <div class="flex-1 min-w-0 flex items-center gap-1.5">
              <span class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50 truncate">{{ cat.name }}</span>
              <span class="text-[10px] font-medium uppercase tracking-wider text-mushroom-400 dark:text-mushroom-500 truncate">{{ cat.group }}</span>
            </div>
            <input
              v-model.number="templateEditValues[cat.name]"
              type="number"
              step="1"
              min="0"
              class="w-24 shrink-0 rounded-lg border border-mushroom-200 dark:border-mushroom-700 bg-white dark:bg-mushroom-900 text-sm py-1 px-2 text-right focus:outline-none focus:ring-1 focus:ring-kangkong-500"
            />
          </div>
        </template>
      </div>
      <div class="flex justify-end gap-2 mt-6 pt-4 border-t border-mushroom-200 dark:border-mushroom-700">
        <button @click="showTemplateEditor = false" class="btn-ghost text-sm">Cancel</button>
        <button @click="saveTemplateEditor" class="btn-primary text-sm" :disabled="templateEditorSaving || Object.keys(templateEditValues).length === 0">
          <span v-if="templateEditorSaving" class="inline-flex items-center gap-1.5">
            <svg class="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            Saving...
          </span>
          <span v-else>Save Template</span>
        </button>
      </div>
    </div>
  </div>
</template>