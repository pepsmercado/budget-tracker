<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { Bar, Doughnut, Line } from 'vue-chartjs'
import Skeleton from '../components/Skeleton.vue'
import { useTheme } from '../composables/useTheme'
import { formatMonthYear, formatCurrency, shortMonth, CHART_COLORS } from '../utils/format.js'
import { currencySymbol } from '../utils/currency.js'
import { EXPENSE_GROUP_ORDER } from '../constants.js'
import api from '../api'

const { isDark } = useTheme()

const props = defineProps({ currency: { type: String, default: 'php' } })

const currencyParam = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')
const curSym = computed(() => currencySymbol(currencyParam.value))

const mode = ref('monthly')
const now = new Date()
const selectedMonth = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const selectedYear = ref(now.getFullYear())

const loading = ref(false)
const monthlyData = ref(null)
const yearlyData = ref(null)

async function fetchMonthly() {
  loading.value = true
  try {
    const { data } = await api.get('/reports/monthly', { params: { month: selectedMonth.value, currency: currencyParam.value } })
    monthlyData.value = data
  } finally {
    loading.value = false
  }
}

async function fetchYearly() {
  loading.value = true
  try {
    const { data } = await api.get('/reports/yearly', { params: { year: selectedYear.value, currency: currencyParam.value } })
    yearlyData.value = data
  } finally {
    loading.value = false
  }
}

function load() {
  if (mode.value === 'monthly') fetchMonthly()
  else fetchYearly()
}

onMounted(load)
watch(mode, load)
watch(selectedMonth, fetchMonthly)
watch(selectedYear, fetchYearly)
watch(currencyParam, load)

function fmt(val) {
  const formatted = formatCurrency(Math.abs(val), curSym.value)
  return val < 0 ? `-${formatted}` : formatted
}

function pctChange(curr, prev) {
  if (!prev || prev === 0) return null
  return ((curr - prev) / Math.abs(prev)) * 100
}

function changeLabel(curr, prev) {
  const p = pctChange(curr, prev)
  if (p === null) return null
  const sign = p > 0 ? '+' : ''
  return `${sign}${p.toFixed(1)}%`
}

function changeClass(curr, prev, invertColor) {
  const p = pctChange(curr, prev)
  if (p === null) return 'text-mushroom-500 dark:text-mushroom-400'
  if (invertColor) return p > 0 ? 'text-tomato-500' : 'text-kangkong-500'
  return p > 0 ? 'text-kangkong-500' : 'text-tomato-500'
}

const noAnim = { animation: false }

const chartTickColor = computed(() => isDark.value ? '#7a6b62' : '#9a887e')
const chartGridColor = computed(() => isDark.value ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)')
const chartLegendColor = computed(() => isDark.value ? '#7a6b62' : '#9a887e')

const monthLabel = computed(() => {
  const [y, m] = selectedMonth.value.split('-')
  return formatMonthYear(parseInt(y), parseInt(m))
})

// ========== MONTHLY ==========
const budgetCategories = computed(() => {
  if (!monthlyData.value?.budget?.categories) return []
  return monthlyData.value.budget.categories.filter(c => c.budget > 0 || c.spent > 0)
})

const budgetedCategoriesOnly = computed(() => {
  if (!monthlyData.value?.budget?.categories) return []
  return monthlyData.value.budget.categories.filter(c => c.budget > 0)
})

const nonBudgetedCategories = computed(() => {
  if (!monthlyData.value?.budget?.categories) return []
  return monthlyData.value.budget.categories.filter(c => c.budget === 0 && c.spent > 0)
})

const prevCategories = computed(() => {
  if (!monthlyData.value?.prev_budget?.categories) return []
  const map = {}
  for (const c of monthlyData.value.prev_budget.categories) map[c.name] = c
  return map
})

const groupedCategories = computed(() => {
  const groups = {}
  for (const cat of budgetedCategoriesOnly.value) {
    const g = cat.group || 'Misc'
    if (!groups[g]) groups[g] = []
    groups[g].push(cat)
  }
  return groups
})

const groupOrder = EXPENSE_GROUP_ORDER
const sortedGroupKeys = computed(() => {
  return groupOrder.filter(g => groupedCategories.value[g]).concat(
    Object.keys(groupedCategories.value).filter(g => !groupOrder.includes(g))
  )
})

function groupSpent(group) {
  return (groupedCategories.value[group] || []).reduce((s, c) => s + c.spent, 0)
}
function groupBudget(group) {
  return (groupedCategories.value[group] || []).reduce((s, c) => s + c.budget, 0)
}

const totalBudget = computed(() => monthlyData.value?.budget?.total_budget || 0)
const totalSpent = computed(() => monthlyData.value?.budget?.total_spent || 0)
const prevTotalSpent = computed(() => monthlyData.value?.prev_budget?.total_spent || 0)
const prevTotalBudget = computed(() => monthlyData.value?.prev_budget?.total_budget || 0)

const accountBalances = computed(() => {
  if (!monthlyData.value?.balances) return []
  return monthlyData.value.balances
})

const totalBalance = computed(() => accountBalances.value.reduce((s, a) => s + a.balance, 0))

const doughnutData = computed(() => {
  const cats = budgetedCategoriesOnly.value.filter(c => c.spent > 0)
  if (!cats.length) return null
  const sorted = [...cats].sort((a, b) => b.spent - a.spent)
  const top = sorted.slice(0, 8)
  const otherSum = sorted.slice(8).reduce((s, c) => s + c.spent, 0)
  const labels = top.map(c => c.name)
  const data = top.map(c => c.spent)
  if (otherSum > 0) { labels.push('Others'); data.push(otherSum) }
  return {
    labels,
    datasets: [{ data, backgroundColor: CHART_COLORS.slice(0, data.length), borderWidth: 0, hoverOffset: 4 }]
  }
})

const doughnutOpts = {
  ...noAnim,
  cutout: '65%',
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.label}: ${fmt(ctx.raw)}`
      }
    }
  }
}

// ========== YEARLY ==========
const annual = computed(() => yearlyData.value?.annual)
const totalIncome = computed(() => annual.value?.total_income || 0)
const totalExpense = computed(() => annual.value?.total_expense || 0)
const totalNet = computed(() => totalIncome.value - totalExpense.value)
const savingsRate = computed(() => {
  if (totalIncome.value === 0) return 0
  return ((totalNet.value / totalIncome.value) * 100)
})

const INCOME_CATS = new Set(['Salary', 'Cashback', 'Interest'])

const monthlyTotals = computed(() => {
  const mc = yearlyData.value?.monthly_categories
  if (!mc) return new Array(12).fill(0)
  const totals = new Array(12).fill(0)
  for (const row of mc) {
    for (const [mon, val] of Object.entries(row.monthly)) {
      if (!val || val <= 0) continue
      const idx = parseInt(mon, 10) - 1
      if (idx >= 0 && idx <= 11) totals[idx] += val
    }
  }
  return totals
})

const activeMonthIndices = computed(() => {
  return monthlyTotals.value
    .map((t, i) => t > 0 ? i : -1)
    .filter(i => i >= 0)
})

const monthlyTrendData = computed(() => {
  const mc = yearlyData.value?.monthly_categories
  if (!mc) return null
  const incomeArr = new Array(12).fill(0)
  const expenseArr = new Array(12).fill(0)
  for (const row of mc) {
    for (const [mon, val] of Object.entries(row.monthly)) {
      if (!val || val <= 0) continue
      const idx = parseInt(mon, 10) - 1
      if (idx < 0 || idx > 11) continue
      if (INCOME_CATS.has(row.category)) incomeArr[idx] += val
      else expenseArr[idx] += val
    }
  }
  const active = activeMonthIndices.value
  if (!active.length) return null
  return {
    labels: active.map(i => shortMonth(i + 1)),
    datasets: [
      { label: 'Income', data: active.map(i => incomeArr[i]), backgroundColor: '#c2652a', borderRadius: 4 },
      { label: 'Expenses', data: active.map(i => expenseArr[i]), backgroundColor: '#c2652a', borderRadius: 4 },
    ],
  }
})

const cumulativeNetData = computed(() => {
  const mc = yearlyData.value?.monthly_categories
  if (!mc) return null
  const monthlyNet = new Array(12).fill(0)
  for (const row of mc) {
    for (const [mon, val] of Object.entries(row.monthly)) {
      if (!val || val <= 0) continue
      const idx = parseInt(mon, 10) - 1
      if (idx < 0 || idx > 11) continue
      if (INCOME_CATS.has(row.category)) monthlyNet[idx] += val
      else monthlyNet[idx] -= val
    }
  }
  const active = activeMonthIndices.value
  if (!active.length) return null
  const labels = []
  const data = []
  let running = 0
  for (const i of active) {
    running += monthlyNet[i]
    labels.push(shortMonth(i + 1))
    data.push(running)
  }
  return {
    labels,
    datasets: [{
      label: 'Cumulative Net',
      data,
      borderColor: '#c2652a',
      backgroundColor: 'rgba(194,101,42,0.08)',
      fill: true,
      tension: 0.3,
      pointRadius: 3,
      pointBackgroundColor: '#c2652a',
    }]
  }
})

const cumulativeNetOpts = computed(() => ({
  ...noAnim,
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: (ctx) => `Net: ${fmt(ctx.raw)}` } }
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: { font: { size: 10 }, color: chartTickColor.value, callback: (v) => formatCurrency(v, curSym.value) },
      grid: { color: chartGridColor.value },
    },
    x: { ticks: { font: { size: 10 }, color: chartTickColor.value }, grid: { display: false } }
  }
}))

const barOpts = computed(() => ({
  ...noAnim,
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top', labels: { usePointStyle: true, pointStyle: 'circle', padding: 16, font: { size: 11 }, color: chartLegendColor.value } },
    tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmt(ctx.raw)}` } }
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: { font: { size: 10 }, color: chartTickColor.value, callback: (v) => formatCurrency(v, curSym.value) },
      grid: { color: chartGridColor.value },
    },
    x: { ticks: { font: { size: 10 }, color: chartTickColor.value }, grid: { display: false } }
  }
}))

const yearlyCategories = computed(() => {
  const mc = yearlyData.value?.monthly_categories
  if (!mc) return []
  const totals = {}
  const groups = {}
  for (const row of mc) {
    for (const [mon, val] of Object.entries(row.monthly)) {
      if (val > 0) {
        totals[row.category] = (totals[row.category] || 0) + val
        groups[row.category] = row.group || 'Misc'
      }
    }
  }
  return Object.entries(totals)
    .map(([name, amount]) => ({ name, amount, group: groups[name] }))
    .sort((a, b) => b.amount - a.amount)
})

const yearlyGroupedCategories = computed(() => {
  const g = {}
  for (const c of yearlyCategories.value) {
    const grp = c.group || 'Misc'
    if (!g[grp]) g[grp] = []
    g[grp].push(c)
  }
  return g
})

const yearlyCatMax = computed(() => {
  if (!yearlyCategories.value.length) return 1
  return yearlyCategories.value[0].amount || 1
})

const yearlyDoughnutData = computed(() => {
  const cats = yearlyCategories.value.filter(c => c.amount > 0)
  if (!cats.length) return null
  const top = cats.slice(0, 8)
  const otherSum = cats.slice(8).reduce((s, c) => s + c.amount, 0)
  const labels = top.map(c => c.name)
  const data = top.map(c => c.amount)
  if (otherSum > 0) { labels.push('Others'); data.push(otherSum) }
  return {
    labels,
    datasets: [{ data, backgroundColor: CHART_COLORS.slice(0, data.length), borderWidth: 0, hoverOffset: 4 }]
  }
})

const monthlySummaries = computed(() => yearlyData.value?.monthly_summary || [])


const activeSummaries = computed(() => {
  const activeSet = new Set(activeMonthIndices.value)
  return monthlySummaries.value.filter((_, i) => activeSet.has(i))
})

const bestMonth = computed(() => {
  const ms = activeSummaries.value.filter(m => (m.total_budget - m.total_spent) >= 0)
  if (!ms.length) return null
  let best = ms[0]
  for (const m of ms) {
    if ((m.total_budget - m.total_spent) > (best.total_budget - best.total_spent)) best = m
  }
  return best
})
const worstMonth = computed(() => {
  const ms = activeSummaries.value.filter(m => (m.total_budget - m.total_spent) < 0)
  if (!ms.length) return null
  let worst = ms[0]
  for (const m of ms) {
    if ((m.total_budget - m.total_spent) < (worst.total_budget - worst.total_spent)) worst = m
  }
  return worst
})

function monthName(ms) {
  const m = parseInt(ms.split('-')[1], 10)
  return shortMonth(m)
}
</script>

<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-medium text-mushroom-950 dark:text-mushroom-50">Reports</h2>
      <div class="flex items-center gap-2 bg-mushroom-200 dark:bg-mushroom-700 rounded-lg p-0.5">
        <button @click="mode = 'monthly'" class="px-3 py-1 text-xs font-medium rounded-md transition-colors" :class="mode === 'monthly' ? 'bg-white dark:bg-mushroom-900 text-mushroom-950 dark:text-mushroom-50 shadow-sm' : 'text-mushroom-700 dark:text-mushroom-300 hover:text-mushroom-700 dark:hover:text-mushroom-200'">Monthly</button>
        <button @click="mode = 'yearly'" class="px-3 py-1 text-xs font-medium rounded-md transition-colors" :class="mode === 'yearly' ? 'bg-white dark:bg-mushroom-900 text-mushroom-950 dark:text-mushroom-50 shadow-sm' : 'text-mushroom-700 dark:text-mushroom-300 hover:text-mushroom-700 dark:hover:text-mushroom-200'">Yearly</button>
      </div>
    </div>

    <!-- Month/Year selector -->
    <div class="flex items-center gap-3">
      <template v-if="mode === 'monthly'">
        <button @click="selectedMonth = (() => { const [y,m] = selectedMonth.split('-').map(Number); const d = new Date(y, m-2, 1); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}` })()" class="text-mushroom-500 dark:text-mushroom-400 hover:text-mushroom-600 dark:hover:text-mushroom-300 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <span class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50 min-w-[160px] text-center">{{ monthLabel }}</span>
        <button @click="selectedMonth = (() => { const [y,m] = selectedMonth.split('-').map(Number); const d = new Date(y, m, 1); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}` })()" class="text-mushroom-500 dark:text-mushroom-400 hover:text-mushroom-600 dark:hover:text-mushroom-300 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </template>
      <template v-else>
        <button @click="selectedYear--" class="text-mushroom-500 dark:text-mushroom-400 hover:text-mushroom-600 dark:hover:text-mushroom-300 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <span class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">{{ selectedYear }}</span>
        <button @click="selectedYear++" class="text-mushroom-500 dark:text-mushroom-400 hover:text-mushroom-600 dark:hover:text-mushroom-300 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </template>
    </div>

    <!-- Skeleton loading -->
    <div v-if="loading" class="space-y-5">
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div v-for="c in 3" :key="c" class="card-elevated p-4 space-y-2">
          <Skeleton width="60px" height="10px" />
          <Skeleton width="120px" height="24px" />
        </div>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div class="card-elevated p-4">
          <Skeleton width="120px" height="12px" class="mb-3" />
          <Skeleton width="100%" height="200px" rounded="rounded-lg" />
        </div>
        <div class="card-elevated p-4 space-y-3">
          <Skeleton width="120px" height="12px" />
          <div v-for="a in 3" :key="a" class="flex justify-between">
            <Skeleton width="80px" height="14px" />
            <Skeleton width="60px" height="14px" />
          </div>
        </div>
      </div>
      <div v-for="g in 2" :key="g" class="card-elevated overflow-hidden">
        <div class="px-4 py-2.5 bg-mushroom-50 dark:bg-mushroom-800 border-b border-mushroom-100 dark:border-mushroom-700/50">
          <Skeleton width="80px" height="10px" />
        </div>
        <div v-for="r in 3" :key="r" class="px-4 py-3 flex items-center justify-between border-b border-mushroom-100 dark:border-mushroom-700/50 last:border-0">
          <div class="flex-1 space-y-1.5">
            <Skeleton width="100px" height="14px" />
            <Skeleton width="100%" height="6px" rounded="rounded-full" />
          </div>
          <Skeleton width="60px" height="14px" />
        </div>
      </div>
    </div>

    <!-- ============ MONTHLY VIEW ============ -->
    <template v-else-if="mode === 'monthly' && monthlyData">
      <!-- Summary row -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div class="card-elevated p-4" style="background-color: #4F5FF0;">
          <div class="text-xs font-semibold mb-1" style="color: #DCE0FE;">Budget</div>
          <div class="text-xl font-bold text-white">{{ fmt(totalBudget) }}</div>
          <div v-if="prevTotalBudget" class="text-[10px] font-semibold mt-1 text-white/70">
            {{ changeLabel(totalBudget, prevTotalBudget) }} vs last month
          </div>
        </div>
        <div class="card-elevated p-4" style="background-color: #F5487D;">
          <div class="text-xs font-semibold mb-1" style="color: #FDD6E2;">Spent</div>
          <div class="text-xl font-bold text-white">{{ fmt(totalSpent) }}</div>
          <div v-if="prevTotalSpent" class="text-[10px] font-semibold mt-1 text-white/70">
            {{ changeLabel(totalSpent, prevTotalSpent) }} vs last month
          </div>
        </div>
        <div class="card-elevated p-4" style="background-color: #14B8A6;">
          <div class="text-xs font-semibold mb-1" style="color: #D3F6F0;">Remaining</div>
          <div class="text-xl font-bold text-white">{{ fmt(totalBudget - totalSpent) }}</div>
          <div class="text-[10px] font-semibold text-white/70 mt-1">
            {{ totalBudget > 0 ? ((totalSpent / totalBudget) * 100).toFixed(0) : 0 }}% of budget used
          </div>
        </div>
      </div>

      <!-- Charts row: Doughnut + top categories -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div class="card-elevated p-4">
          <h3 class="text-xs font-medium text-mushroom-700 dark:text-mushroom-400 mb-2">Spending Breakdown</h3>
          <div class="h-48 flex items-center justify-center">
            <Doughnut v-if="doughnutData" :data="doughnutData" :options="doughnutOpts" class="max-h-48" />
            <span v-else class="text-xs text-mushroom-300">No spending data</span>
          </div>
          <div v-if="doughnutData" class="mt-2 space-y-1">
            <div v-for="(label, i) in doughnutData.labels.slice(0, 5)" :key="label" class="flex items-center justify-between text-[10px]">
              <div class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full flex-shrink-0" :style="{ backgroundColor: doughnutData.datasets[0].backgroundColor[i] }" />
                <span class="text-mushroom-600 dark:text-mushroom-400 truncate">{{ label }}</span>
              </div>
              <span class="text-mushroom-950 dark:text-mushroom-50 font-medium">{{ fmt(doughnutData.datasets[0].data[i]) }}</span>
            </div>
          </div>
        </div>

        <div class="card-elevated p-4">
          <h3 class="text-xs font-medium text-mushroom-700 dark:text-mushroom-400 mb-2">Account Balances</h3>
          <div class="space-y-2.5">
            <div v-for="acc in accountBalances" :key="acc.account_id" class="flex items-center justify-between">
              <span class="text-sm text-mushroom-700 dark:text-mushroom-300">{{ acc.account_name }}</span>
              <span class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">{{ fmt(acc.balance) }}</span>
            </div>
            <div class="pt-2 border-t border-mushroom-100 dark:border-mushroom-700/50 flex items-center justify-between">
              <span class="text-xs font-medium text-mushroom-700 dark:text-mushroom-400">Total</span>
              <span class="text-sm font-semibold text-mushroom-950 dark:text-mushroom-50">{{ fmt(totalBalance) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Grouped categories (budgeted) -->
      <div class="space-y-3">
        <div v-for="group in sortedGroupKeys" :key="group" class="card-elevated overflow-hidden">
          <div class="px-4 py-2.5 border-b border-mushroom-100 dark:border-mushroom-700/50 flex items-center justify-between bg-mushroom-100 dark:bg-mushroom-700">
            <span class="text-xs font-semibold uppercase tracking-wider text-mushroom-700 dark:text-mushroom-400">{{ group }}</span>
            <span class="text-xs text-mushroom-500 dark:text-mushroom-400">{{ fmt(groupSpent(group)) }} / {{ fmt(groupBudget(group)) }}</span>
          </div>
          <div class="divide-y divide-mushroom-100 dark:divide-mushroom-700/50">
            <div v-for="cat in groupedCategories[group]" :key="cat.name" class="px-4 py-2.5 flex items-center justify-between">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-sm text-mushroom-950 dark:text-mushroom-50">{{ cat.name }}</span>
                  <span v-if="prevCategories[cat.name]" class="text-[10px]" :class="changeClass(cat.spent, prevCategories[cat.name].spent, true)">
                    {{ changeLabel(cat.spent, prevCategories[cat.name].spent) }}
                  </span>
                </div>
                <div class="w-full bg-mushroom-200 dark:bg-mushroom-700 rounded-full h-1.5 mt-1.5">
                  <div class="h-1.5 rounded-full transition-all" :class="cat.budget > 0 && cat.spent / cat.budget > 0.9 ? 'bg-tomato-400' : 'bg-kangkong-400'" :style="{ width: cat.budget > 0 ? Math.min((cat.spent / cat.budget) * 100, 100) + '%' : '0%' }" />
                </div>
              </div>
              <div class="ml-3 text-right flex-shrink-0 w-32">
                <div class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">{{ fmt(cat.spent) }}</div>
                <div class="text-[10px] text-mushroom-500 dark:text-mushroom-400">of {{ fmt(cat.budget) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Non-budgeted expenses -->
      <div v-if="nonBudgetedCategories.length" class="card-elevated overflow-hidden">
        <div class="px-4 py-2.5 border-b border-mushroom-100 dark:border-mushroom-700/50 bg-mushroom-100 dark:bg-mushroom-700">
          <span class="text-xs font-semibold uppercase tracking-wider text-mushroom-700 dark:text-mushroom-400">Non-budgeted</span>
        </div>
        <div class="divide-y divide-mushroom-100 dark:divide-mushroom-700/50">
          <div v-for="cat in nonBudgetedCategories" :key="cat.name" class="px-4 py-2.5 flex items-center justify-between">
            <div class="flex-1 min-w-0">
              <span class="text-sm text-mushroom-950 dark:text-mushroom-50">{{ cat.name }}</span>
              <div class="text-[10px] text-mushroom-500 dark:text-mushroom-400 mt-0.5">{{ cat.group || 'Misc' }}</div>
            </div>
            <span class="ml-3 text-sm font-medium text-mushroom-950 dark:text-mushroom-50 flex-shrink-0 w-28 text-right">{{ fmt(cat.spent) }}</span>
          </div>
        </div>
        <div class="px-4 py-2 bg-mushroom-50/50 dark:bg-mushroom-800/50 border-t border-mushroom-100 dark:border-mushroom-700/50 flex items-center justify-between text-xs">
          <span class="text-mushroom-700 dark:text-mushroom-400">Total non-budgeted</span>
          <span class="font-medium text-mushroom-950 dark:text-mushroom-50">{{ fmt(nonBudgetedCategories.reduce((s, c) => s + c.spent, 0)) }}</span>
        </div>
      </div>
    </template>

    <!-- ============ YEARLY VIEW ============ -->
    <template v-else-if="mode === 'yearly' && yearlyData">
      <!-- Summary cards -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div class="card-elevated p-4 bg-kangkong-400 dark:bg-kangkong-500/10">
          <div class="text-xs font-semibold text-white dark:text-kangkong-300 mb-1">Total Income</div>
          <div class="text-xl font-bold text-white dark:text-kangkong-200">{{ fmt(totalIncome) }}</div>
        </div>
        <div class="card-elevated p-4 bg-tomato-400 dark:bg-tomato-500/10">
          <div class="text-xs font-semibold text-white dark:text-tomato-300 mb-1">Total Expenses</div>
          <div class="text-xl font-bold text-white dark:text-tomato-200">{{ fmt(totalExpense) }}</div>
        </div>
        <div class="card-elevated p-4 bg-purple-400 dark:bg-purple-500/10">
          <div class="text-xs font-semibold text-white dark:text-purple-300 mb-1">Savings</div>
          <div class="text-xl font-bold text-white dark:text-purple-200">{{ totalNet >= 0 ? '+' : '-' }}{{ fmt(totalNet) }}</div>
        </div>
        <div class="card-elevated p-4 bg-indigo-400 dark:bg-indigo-500/10">
          <div class="text-xs font-semibold text-white dark:text-indigo-300 mb-1">Savings Rate</div>
          <div class="text-xl font-bold text-white dark:text-indigo-200">{{ savingsRate.toFixed(1) }}%</div>
        </div>
      </div>

      <!-- Monthly trend + cumulative net -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div class="card-elevated p-4">
          <h3 class="text-xs font-medium text-mushroom-700 dark:text-mushroom-400 mb-3">Monthly Income vs Expenses</h3>
          <div class="h-56">
            <Bar v-if="monthlyTrendData" :data="monthlyTrendData" :options="barOpts" />
          </div>
        </div>
        <div class="card-elevated p-4">
          <h3 class="text-xs font-medium text-mushroom-700 dark:text-mushroom-400 mb-3">Cumulative Net Savings</h3>
          <div class="h-56">
            <Line v-if="cumulativeNetData" :data="cumulativeNetData" :options="cumulativeNetOpts" />
          </div>
        </div>
      </div>

      <!-- Doughnut + best/worst month -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div class="card-elevated p-4">
          <h3 class="text-xs font-medium text-mushroom-700 dark:text-mushroom-400 mb-2">Expense Breakdown</h3>
          <div class="h-48 flex items-center justify-center">
            <Doughnut v-if="yearlyDoughnutData" :data="yearlyDoughnutData" :options="doughnutOpts" class="max-h-48" />
          </div>
          <div v-if="yearlyDoughnutData" class="mt-2 space-y-1">
            <div v-for="(label, i) in yearlyDoughnutData.labels.slice(0, 5)" :key="label" class="flex items-center justify-between text-[10px]">
              <div class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full flex-shrink-0" :style="{ backgroundColor: yearlyDoughnutData.datasets[0].backgroundColor[i] }" />
                <span class="text-mushroom-600 dark:text-mushroom-400 truncate">{{ label }}</span>
              </div>
              <span class="text-mushroom-950 dark:text-mushroom-50 font-medium">{{ fmt(yearlyDoughnutData.datasets[0].data[i]) }}</span>
            </div>
          </div>
        </div>
        <div class="card-elevated p-4">
          <h3 class="text-xs font-medium text-mushroom-700 dark:text-mushroom-400 mb-3">Month Highlights</h3>
          <div class="space-y-4">
            <div v-if="bestMonth" class="p-3 rounded-lg bg-kangkong-50 dark:bg-kangkong-500/15 border border-kangkong-100 dark:border-kangkong-500/20">
              <div class="text-[10px] font-medium text-kangkong-600 dark:text-kangkong-400 uppercase tracking-wider mb-1">Best Month</div>
              <div class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">{{ monthName(bestMonth.month) }}</div>
              <div class="text-xs text-mushroom-700 dark:text-mushroom-400 mt-0.5">Net: <span class="text-kangkong-600 font-medium">{{ fmt(bestMonth.total_budget - bestMonth.total_spent) }} under budget</span></div>
            </div>
            <div v-if="worstMonth" class="p-3 rounded-lg bg-tomato-50 dark:bg-tomato-500/10 border border-tomato-100 dark:border-tomato-500/20">
              <div class="text-[10px] font-medium text-tomato-600 uppercase tracking-wider mb-1">Over Budget</div>
              <div class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">{{ monthName(worstMonth.month) }}</div>
              <div class="text-xs text-mushroom-700 dark:text-mushroom-400 mt-0.5">Net: <span class="text-tomato-600 font-medium">{{ fmt(Math.abs(worstMonth.total_budget - worstMonth.total_spent)) }} over budget</span></div>
            </div>
            <div class="p-3 rounded-lg bg-mushroom-100 dark:bg-mushroom-700 border border-mushroom-100 dark:border-mushroom-700">
              <div class="text-[10px] font-medium text-mushroom-700 dark:text-mushroom-400 uppercase tracking-wider mb-1">Average Monthly Spend</div>
              <div class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">{{ fmt(activeSummaries.length ? totalExpense / activeSummaries.length : 0) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Monthly MoM table -->
      <div class="card-elevated overflow-hidden">
        <div class="px-4 py-3 border-b border-mushroom-100 dark:border-mushroom-700/50">
          <h3 class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">Month-by-Month</h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-mushroom-100 dark:border-mushroom-700/50">
                <th class="px-4 py-2 text-left font-medium text-mushroom-700 dark:text-mushroom-400">Month</th>
                <th class="px-4 py-2 text-right font-medium text-mushroom-700 dark:text-mushroom-400">Budget</th>
                <th class="px-4 py-2 text-right font-medium text-mushroom-700 dark:text-mushroom-400">Spent</th>
                <th class="px-4 py-2 text-right font-medium text-mushroom-700 dark:text-mushroom-400">Remaining</th>
                <th class="px-4 py-2 text-right font-medium text-mushroom-700 dark:text-mushroom-400">% Used</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="ms in activeSummaries" :key="ms.month" class="border-b border-mushroom-50 hover:bg-mushroom-100 dark:hover:bg-mushroom-700 transition-colors">
                <td class="px-4 py-2 font-medium text-mushroom-950 dark:text-mushroom-50">{{ monthName(ms.month) }}</td>
                <td class="px-4 py-2 text-right text-mushroom-600 dark:text-mushroom-400">{{ fmt(ms.total_budget) }}</td>
                <td class="px-4 py-2 text-right" :class="ms.total_spent > ms.total_budget ? 'text-tomato-600' : 'text-mushroom-600 dark:text-mushroom-400'">{{ fmt(ms.total_spent) }}</td>
                <td class="px-4 py-2 text-right" :class="(ms.total_budget - ms.total_spent) >= 0 ? 'text-kangkong-600' : 'text-tomato-600'">{{ fmt(ms.total_budget - ms.total_spent) }}</td>
                <td class="px-4 py-2 text-right">
                  <span class="inline-flex items-center gap-1">
                    <span class="w-12 bg-mushroom-200 dark:bg-mushroom-700 rounded-full h-1 inline-block">
                      <span class="h-1 rounded-full inline-block" :class="ms.total_budget > 0 && ms.total_spent / ms.total_budget > 0.9 ? 'bg-tomato-400' : 'bg-kangkong-400'" :style="{ width: ms.total_budget > 0 ? Math.min((ms.total_spent / ms.total_budget) * 100, 100) + '%' : '0%', display: 'inline-block' }" />
                    </span>
                    <span class="text-mushroom-700 dark:text-mushroom-400">{{ ms.total_budget > 0 ? ((ms.total_spent / ms.total_budget) * 100).toFixed(0) : 0 }}%</span>
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Grouped yearly category totals -->
      <div class="space-y-3">
        <div v-for="(cats, group) in yearlyGroupedCategories" :key="group" class="card-elevated overflow-hidden">
          <div class="px-4 py-2.5 border-b border-mushroom-100 dark:border-mushroom-700/50 bg-mushroom-100 dark:bg-mushroom-700">
            <span class="text-xs font-semibold uppercase tracking-wider text-mushroom-700 dark:text-mushroom-400">{{ group }}</span>
          </div>
          <div class="divide-y divide-mushroom-100 dark:divide-mushroom-700/50">
            <div v-for="cat in cats" :key="cat.name" class="px-4 py-2.5 flex items-center justify-between">
              <div class="flex-1 min-w-0">
                <div class="text-sm text-mushroom-950 dark:text-mushroom-50">{{ cat.name }}</div>
                <div class="w-full bg-mushroom-200 dark:bg-mushroom-700 rounded-full h-1.5 mt-1.5">
                  <div class="h-1.5 rounded-full bg-kangkong-400 transition-all" :style="{ width: (cat.amount / yearlyCatMax * 100) + '%' }" />
                </div>
              </div>
              <span class="ml-3 text-sm font-medium text-mushroom-950 dark:text-mushroom-50 flex-shrink-0 w-28 text-right">{{ fmt(cat.amount) }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
