<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { Line, Doughnut } from 'vue-chartjs'
import { useSummary } from '../composables/useSummary'
import { useAccounts } from '../composables/useAccounts'
import { useTransactions } from '../composables/useTransactions'
import { useTheme } from '../composables/useTheme'
import api from '../api'
import Skeleton from '../components/Skeleton.vue'

const { isDark } = useTheme()

const props = defineProps({ currency: { type: String, default: 'php' } })

const { summary, balances, fetchSummary, fetchBalances } = useSummary()
const { accounts, fetchAccounts } = useAccounts()
const { transactions, fetchTransactions } = useTransactions()

const currentYear = new Date().getFullYear()
const categories = ref([])
const selectedMonth = ref('')
const drilledGroup = ref(null)
const expenseMatrixMode = ref('category')
const incomeMatrixMode = ref('category')
const showAverages = ref(false)
const selectedYear = ref(currentYear)
const pieYear = ref(currentYear)
const pieMonths = ref([])

const loading = ref(true)
const trendChartRef = ref(null)
const incomeVisible = ref(true)
const expensesVisible = ref(true)
const budgetSummary = ref(null)

const currencyParam = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')
const currencySymbol = computed(() => props.currency === 'usd' ? '$' : '₱')
const viewLabel = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')

const currentMonth = computed(() => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
})

function toggleIncome() {
  if (incomeVisible.value && expensesVisible.value) {
    expensesVisible.value = false
  } else if (!incomeVisible.value) {
    incomeVisible.value = true
    expensesVisible.value = true
  } else {
    incomeVisible.value = true
  }
  updateChartVisibility()
}

function toggleExpenses() {
  if (incomeVisible.value && expensesVisible.value) {
    incomeVisible.value = false
  } else if (!expensesVisible.value) {
    incomeVisible.value = true
    expensesVisible.value = true
  } else {
    expensesVisible.value = true
  }
  updateChartVisibility()
}

function updateChartVisibility() {
  const chart = trendChartRef.value?.chart
  if (!chart) return
  chart.data.datasets[0].hidden = !incomeVisible.value
  chart.data.datasets[1].hidden = !expensesVisible.value
  chart.update()
}

const years = computed(() => [currentYear, currentYear - 1, currentYear - 2])

const months = computed(() => {
  if (!summary.value) return []
  return summary.value.monthly.map(m => {
    const [y, mo] = m.month.split('-')
    const date = new Date(y, parseInt(mo) - 1)
    return { value: m.month, label: date.toLocaleString('en-US', { month: 'short' }) }
  })
})

async function fetchPieMonths() {
  const { data } = await api.get(`/summary/${pieYear.value}`, { params: { currency: currencyParam.value } })
  pieMonths.value = [
    { value: 'full-year', label: 'Full Year' },
    ...data.monthly.map(m => {
      const [y, mo] = m.month.split('-')
      const date = new Date(y, parseInt(mo) - 1)
      return { value: m.month, label: date.toLocaleString('en-US', { month: 'short' }) }
    })
  ]
  if (!pieMonths.value.find(m => m.value === selectedMonth.value)) {
    selectedMonth.value = pieMonths.value[pieMonths.value.length - 1].value
  }
}

async function fetchCategories() {
  const { data } = await api.get('/categories')
  categories.value = data
}

const categoryToGroup = computed(() => {
  const map = {}
  for (const c of categories.value) {
    if (c.type === 'expense') {
      map[c.name] = c.group
    }
  }
  return map
})

const GROUP_ORDER = ['Fixed', 'Essential', 'Lifestyle', 'School', 'Misc', 'Sinking']
function groupSortKey(name) {
  const idx = GROUP_ORDER.indexOf(name)
  return idx >= 0 ? idx : GROUP_ORDER.length
}

async function loadDashboard() {
  await fetchCategories()
  await Promise.all([fetchSummary(currentYear, currencyParam.value), fetchBalances(currencyParam.value), fetchAccounts(), fetchMatrixData(), fetchPieMonths(), fetchCurrentMonthSummary()])
  await Promise.all([fetchExpenseAccountMatrix(), fetchIncomeMatrixData(), fetchIncomeAccountMatrix()])
  if (months.value.length > 0) {
    selectedMonth.value = months.value[months.value.length - 1].value
  }
  const { data: summary } = await api.get(`/budgets/${currentMonth.value}/summary`, { params: { currency: currencyParam.value } }).catch(() => ({ data: null }))
  budgetSummary.value = summary
  loading.value = false
}

onMounted(loadDashboard)

watch(currencyParam, loadDashboard)

const currentMonthBudget = ref(null)
const currentMonthIncome = ref(0)
const currentMonthExpense = ref(0)

async function fetchCurrentMonthSummary() {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const monthKey = `${y}-${m}`

  const [budgetRes, txnsRes] = await Promise.all([
    api.get(`/budgets/${monthKey}`).catch(() => null),
    api.get(`/transactions`, { params: { currency: currencyParam.value, start_date: `${y}-${m}-01`, end_date: `${y}-${m}-${new Date(y, parseInt(m), 0).getDate()}` } })
  ])

  if (budgetRes?.data) currentMonthBudget.value = budgetRes.data

  const txns = txnsRes.data || []
  currentMonthIncome.value = txns.filter(t => t.type === 'income').reduce((s, t) => s + t.amount, 0)
  currentMonthExpense.value = txns.filter(t => t.type === 'expense').reduce((s, t) => s + t.amount, 0)
}

const budgetProgress = computed(() => {
  if (!currentMonthBudget.value || !currentMonthBudget.value.total_budget) return 0
  return Math.round((currentMonthExpense.value / currentMonthBudget.value.total_budget) * 100)
})

const budgetRemaining = computed(() => {
  if (!currentMonthBudget.value) return 0
  return currentMonthBudget.value.total_budget - currentMonthExpense.value
})

watch(pieYear, async () => {
  await fetchPieMonths()
})

const monthlyChartData = computed(() => {
  if (!summary.value) return { labels: [], datasets: [] }
  return {
    labels: summary.value.monthly.map(m => {
      const [y, mo] = m.month.split('-')
      const date = new Date(y, parseInt(mo) - 1)
      return date.toLocaleString('en-US', { month: 'short' })
    }),
    datasets: [
      {
        label: 'Income',
        data: summary.value.monthly.map(m => Math.round(m.income)),
        borderColor: '#17ad49',
        backgroundColor: 'rgba(23, 173, 73, 0.08)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: '#17ad49',
      },
      {
        label: 'Expense',
        data: summary.value.monthly.map(m => Math.round(m.expense)),
        borderColor: '#da2f38',
        backgroundColor: 'rgba(218, 47, 56, 0.08)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: '#da2f38',
      },
    ],
  }
})

const monthlyTransactions = ref([])
watch(selectedMonth, async (val) => {
  if (!val) return
  if (val === 'full-year') {
    await fetchTransactions({ currency: currencyParam.value, start_date: `${pieYear.value}-01-01`, end_date: `${pieYear.value}-12-31` })
  } else {
    const [y, m] = val.split('-')
    const lastDay = new Date(parseInt(y), parseInt(m), 0).getDate()
    await fetchTransactions({ currency: currencyParam.value, start_date: `${y}-${m}-01`, end_date: `${y}-${m}-${lastDay}` })
  }
  monthlyTransactions.value = transactions.value.filter(t => t.type === 'expense')
}, { immediate: true })

function pctTooltip(context) {
  const label = context.label || ''
  const value = context.parsed || 0
  const dataset = context.dataset
  const total = dataset.data.reduce((a, b) => a + b, 0)
  if (total === 0) return label
  const pct = ((value / total) * 100).toFixed(1)
  return `${label}: ${pct}%`
}

const chartTickColor = computed(() => isDark.value ? '#b0b8b6' : '#5c6b61')
const chartGridColor = computed(() => isDark.value ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)')
const chartLegendColor = computed(() => isDark.value ? '#b0b8b6' : '#5c6b61')

const trendLineOpts = computed(() => ({
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    y: { grid: { color: chartGridColor.value }, ticks: { font: { size: 10 }, color: chartTickColor.value } },
    x: { grid: { display: false }, ticks: { font: { size: 10 }, color: chartTickColor.value } }
  }
}))

const doughnutOpts = computed(() => ({
  responsive: true, maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom', labels: { usePointStyle: true, padding: 8, font: { size: 10 }, color: chartLegendColor.value } },
    tooltip: { callbacks: { label: pctTooltip } },
    cutout: '55%'
  },
  onClick: () => { drilledGroup.value = null }
}))

const groupChartData = computed(() => {
  const txns = monthlyTransactions.value
  if (!txns.length) return { labels: [], datasets: [] }

  const groups = {}
  for (const t of txns) {
    const group = categoryToGroup.value[t.category] || 'Others'
    if (!groups[group]) groups[group] = 0
    groups[group] += t.amount
  }
  const sorted = Object.entries(groups).sort((a, b) => groupSortKey(a[0]) - groupSortKey(b[0]))
  const colors = ['#da2f38', '#17ad49', '#8952f6', '#1679fa', '#ff970a', '#0592b5', '#738482']
  return {
    labels: sorted.map(([g]) => g),
    datasets: [{
      data: sorted.map(([, v]) => Math.round(v)),
      backgroundColor: sorted.map((_, i) => colors[i % colors.length]),
      borderWidth: 0,
      hoverOffset: 4,
    }],
  }
})

const drilledChartData = computed(() => {
  if (!drilledGroup.value) return null
  const txns = monthlyTransactions.value
  const cats = {}
  for (const t of txns) {
    const group = categoryToGroup.value[t.category] || 'Others'
    if (group === drilledGroup.value) {
      if (!cats[t.category]) cats[t.category] = 0
      cats[t.category] += t.amount
    }
  }
  const sorted = Object.entries(cats).sort((a, b) => b[1] - a[1])
  const colors = ['#da2f38', '#ff970a', '#ffdf1b', '#f6737a', '#ffb132', '#ffd16d']
  return {
    labels: sorted.map(([c]) => c),
    datasets: [{
      data: sorted.map(([, v]) => Math.round(v)),
      backgroundColor: sorted.map((_, i) => colors[i % colors.length]),
      borderWidth: 0,
      hoverOffset: 4,
    }],
  }
})

watch(selectedYear, async () => {
  await Promise.all([fetchMatrixData(), fetchExpenseAccountMatrix(), fetchIncomeMatrixData(), fetchIncomeAccountMatrix()])
})

const matrixRows = ref([])
const matrixMonths = ref([])
const matrixMonthlyTotals = ref([])
const matrixGrandTotal = ref(0)
const matrixAvg = ref(0)

async function fetchMatrixData() {
  const { data } = await api.get(`/summary/${selectedYear.value}/monthly-categories`, { params: { currency: currencyParam.value } })
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  matrixMonths.value = monthNames

  const groups = {}
  for (const row of data) {
    const group = categoryToGroup.value[row.category] || 'Others'
    if (!groups[group]) groups[group] = []
    groups[group].push(row)
  }

  const sortedGroups = Object.entries(groups).sort((a, b) => groupSortKey(a[0]) - groupSortKey(b[0]))

  const rows = []
  const monthlyTotals = new Array(12).fill(0)
  let grandTotal = 0

  for (const [group, cats] of sortedGroups) {
    rows.push({ type: 'group', name: group })
    const groupTotals = new Array(12).fill(0)
    for (const cat of cats) {
      const rowData = new Array(12).fill(0)
      let catTotal = 0
      for (let i = 0; i < 12; i++) {
        const m = String(i + 1).padStart(2, '0')
        const val = cat.monthly[m] || 0
        rowData[i] = Math.round(val)
        groupTotals[i] += rowData[i]
        monthlyTotals[i] += rowData[i]
        catTotal += rowData[i]
      }
      rows.push({ type: 'category', name: cat.category, data: rowData, group })
      grandTotal += catTotal
    }
    rows.push({ type: 'groupTotal', name: group, data: groupTotals })
  }

  matrixRows.value = rows
  matrixMonthlyTotals.value = monthlyTotals
  matrixGrandTotal.value = grandTotal
  matrixAvg.value = Math.round(grandTotal / 12)

  const allGroups = new Set()
  for (const row of rows) {
    if (row.type === 'group') allGroups.add(row.name)
  }
  if (collapsedGroups.value.size === 0) {
    collapsedGroups.value = allGroups
  }
}

const collapsedGroups = ref(new Set())

function toggleGroupCollapse(groupName) {
  if (collapsedGroups.value.has(groupName)) {
    collapsedGroups.value.delete(groupName)
  } else {
    collapsedGroups.value.add(groupName)
  }
  collapsedGroups.value = new Set(collapsedGroups.value)
}

function isGroupCollapsed(groupName) {
  return collapsedGroups.value.has(groupName)
}

const expenseAccountRows = ref([])
const expenseAccountMonthlyTotals = ref([])
const expenseAccountGrandTotal = ref(0)
const expenseAccountCollapsed = ref(new Set())

function toggleExpenseAccountCollapse(typeName) {
  if (expenseAccountCollapsed.value.has(typeName)) {
    expenseAccountCollapsed.value.delete(typeName)
  } else {
    expenseAccountCollapsed.value.add(typeName)
  }
  expenseAccountCollapsed.value = new Set(expenseAccountCollapsed.value)
}

function isExpenseAccountCollapsed(typeName) {
  return expenseAccountCollapsed.value.has(typeName)
}

const ACCOUNT_TYPE_ORDER = ['savings', 'checking', 'time_deposit', 'equity', 'investment']

async function fetchExpenseAccountMatrix() {
  const { data: txnsData } = await api.get(`/transactions`, { params: { currency: currencyParam.value, start_date: `${selectedYear.value}-01-01`, end_date: `${selectedYear.value}-12-31`, type: 'expense' } })

  const grouped = {}
  for (const t of txnsData) {
    const acc = accounts.value.find(a => a.id === t.account_id)
    const accType = acc ? acc.type : 'other'
    if (accType === 'time_deposit' || accType === 'investment' || accType === 'equity') continue
    const accName = acc ? acc.name : t.account_id
    if (!grouped[accType]) grouped[accType] = {}
    if (!grouped[accType][accName]) grouped[accType][accName] = new Array(12).fill(0)
    const d = new Date(t.date)
    const monthIdx = d.getMonth()
    grouped[accType][accName][monthIdx] += t.amount
  }

  const sortedTypes = Object.keys(grouped).sort((a, b) => {
    const ai = ACCOUNT_TYPE_ORDER.indexOf(a)
    const bi = ACCOUNT_TYPE_ORDER.indexOf(b)
    return (ai >= 0 ? ai : 99) - (bi >= 0 ? bi : 99)
  })

  const rows = []
  const monthlyTotals = new Array(12).fill(0)
  let grandTotal = 0

  for (const type of sortedTypes) {
    const accs = grouped[type]
    rows.push({ type: 'group', name: type })
    const typeTotals = new Array(12).fill(0)
    const sortedAccs = Object.entries(accs).sort((a, b) => b[1].reduce((s, v) => s + v, 0) - a[1].reduce((s, v) => s + v, 0))
    for (const [accName, accData] of sortedAccs) {
      const rowData = accData.map(v => Math.round(v))
      let accTotal = 0
      for (let i = 0; i < 12; i++) {
        typeTotals[i] += rowData[i]
        monthlyTotals[i] += rowData[i]
        accTotal += rowData[i]
      }
      rows.push({ type: 'account', name: accName, data: rowData, group: type })
      grandTotal += accTotal
    }
    rows.push({ type: 'groupTotal', name: type, data: typeTotals })
  }

  expenseAccountRows.value = rows
  expenseAccountMonthlyTotals.value = monthlyTotals
  expenseAccountGrandTotal.value = grandTotal

  const allTypes = new Set()
  for (const row of rows) {
    if (row.type === 'group') allTypes.add(row.name)
  }
  if (expenseAccountCollapsed.value.size === 0) {
    expenseAccountCollapsed.value = allTypes
  }
}

const incomeMatrixRows = ref([])
const incomeMatrixMonths = ref([])
const incomeMatrixMonthlyTotals = ref([])
const incomeMatrixGrandTotal = ref(0)
const incomeMatrixAvg = ref(0)

async function fetchIncomeMatrixData() {
  const { data } = await api.get(`/transactions`, { params: { currency: currencyParam.value, start_date: `${selectedYear.value}-01-01`, end_date: `${selectedYear.value}-12-31`, type: 'income' } })
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  incomeMatrixMonths.value = monthNames

  const cats = {}
  for (const t of data) {
    if (!cats[t.category]) cats[t.category] = new Array(12).fill(0)
    const d = new Date(t.date)
    cats[t.category][d.getMonth()] += t.amount
  }

  const rows = []
  const monthlyTotals = new Array(12).fill(0)
  let grandTotal = 0

  for (const [cat, catData] of Object.entries(cats)) {
    const rowData = catData.map(v => Math.round(v))
    let catTotal = 0
    for (let i = 0; i < 12; i++) {
      monthlyTotals[i] += rowData[i]
      catTotal += rowData[i]
    }
    rows.push({ type: 'category', name: cat, data: rowData })
    grandTotal += catTotal
  }

  rows.sort((a, b) => {
    const order = ['Salary', 'Interest', 'Cashback', 'Others']
    return order.indexOf(a.name) - order.indexOf(b.name)
  })

  incomeMatrixRows.value = rows
  incomeMatrixMonthlyTotals.value = monthlyTotals
  incomeMatrixGrandTotal.value = grandTotal
  incomeMatrixAvg.value = Math.round(grandTotal / 12)
}

const incomeAccountRows = ref([])
const incomeAccountMonthlyTotals = ref([])
const incomeAccountGrandTotal = ref(0)
const incomeAccountCollapsed = ref(new Set())

function toggleIncomeAccountCollapse(typeName) {
  if (incomeAccountCollapsed.value.has(typeName)) {
    incomeAccountCollapsed.value.delete(typeName)
  } else {
    incomeAccountCollapsed.value.add(typeName)
  }
  incomeAccountCollapsed.value = new Set(incomeAccountCollapsed.value)
}

function isIncomeAccountCollapsed(typeName) {
  return incomeAccountCollapsed.value.has(typeName)
}

async function fetchIncomeAccountMatrix() {
  const { data: txnsData } = await api.get(`/transactions`, { params: { currency: currencyParam.value, start_date: `${selectedYear.value}-01-01`, end_date: `${selectedYear.value}-12-31`, type: 'income' } })

  const grouped = {}
  for (const t of txnsData) {
    const acc = accounts.value.find(a => a.id === t.account_id)
    const accType = acc ? acc.type : 'other'
    if (accType === 'checking') continue
    const accName = acc ? acc.name : t.account_id
    if (!grouped[accType]) grouped[accType] = {}
    if (!grouped[accType][accName]) grouped[accType][accName] = new Array(12).fill(0)
    const d = new Date(t.date)
    const monthIdx = d.getMonth()
    grouped[accType][accName][monthIdx] += t.amount
  }

  const sortedTypes = Object.keys(grouped).sort((a, b) => {
    const ai = ACCOUNT_TYPE_ORDER.indexOf(a)
    const bi = ACCOUNT_TYPE_ORDER.indexOf(b)
    return (ai >= 0 ? ai : 99) - (bi >= 0 ? bi : 99)
  })

  const rows = []
  const monthlyTotals = new Array(12).fill(0)
  let grandTotal = 0

  for (const type of sortedTypes) {
    const accs = grouped[type]
    rows.push({ type: 'group', name: type })
    const typeTotals = new Array(12).fill(0)
    const sortedAccs = Object.entries(accs).sort((a, b) => b[1].reduce((s, v) => s + v, 0) - a[1].reduce((s, v) => s + v, 0))
    for (const [accName, accData] of sortedAccs) {
      const rowData = accData.map(v => Math.round(v))
      let accTotal = 0
      for (let i = 0; i < 12; i++) {
        typeTotals[i] += rowData[i]
        monthlyTotals[i] += rowData[i]
        accTotal += rowData[i]
      }
      rows.push({ type: 'account', name: accName, data: rowData, group: type })
      grandTotal += accTotal
    }
    rows.push({ type: 'groupTotal', name: type, data: typeTotals })
  }

  incomeAccountRows.value = rows
  incomeAccountMonthlyTotals.value = monthlyTotals
  incomeAccountGrandTotal.value = grandTotal

  const allTypes = new Set()
  for (const row of rows) {
    if (row.type === 'group') allTypes.add(row.name)
  }
  if (incomeAccountCollapsed.value.size === 0) {
    incomeAccountCollapsed.value = allTypes
  }
}

function formatConverted(val) {
  return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-medium text-mushroom-950 dark:text-mushroom-50">{{ viewLabel }} Dashboard</h2>
      <div class="flex items-center gap-3">
        <span class="text-xs text-mushroom-400 dark:text-mushroom-500">{{ currentYear }}</span>
      </div>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div v-for="i in 3" :key="i" class="card-elevated p-4 space-y-2">
          <Skeleton width="40%" height="0.75rem" />
          <Skeleton width="30%" height="1.25rem" />
          <Skeleton width="100%" height="0.5rem" />
          <Skeleton width="60%" height="0.625rem" />
        </div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="card-elevated p-4 space-y-2">
          <Skeleton width="35%" height="0.875rem" />
          <Skeleton height="12rem" />
          <div class="flex justify-center gap-4">
            <Skeleton width="3rem" height="0.625rem" />
            <Skeleton width="3rem" height="0.625rem" />
          </div>
        </div>
        <div class="card-elevated p-4 space-y-2">
          <Skeleton width="40%" height="0.875rem" />
          <Skeleton height="12rem" />
        </div>
      </div>
      <div class="card-elevated p-4 space-y-3">
        <Skeleton width="30%" height="0.875rem" />
        <div class="space-y-2">
          <Skeleton v-for="i in 4" :key="i" height="2rem" />
        </div>
      </div>
      <div class="card-elevated p-4 space-y-3">
        <Skeleton width="35%" height="0.875rem" />
        <div class="space-y-2">
          <Skeleton v-for="i in 4" :key="i" height="2rem" />
        </div>
      </div>
    </template>

    <template v-else>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="card-elevated p-4">
        <div class="text-xs text-mushroom-400 dark:text-mushroom-500 mb-1">Budget Status</div>
        <div class="text-lg font-semibold text-mushroom-950 dark:text-mushroom-50">
          {{ budgetProgress }}%
        </div>
        <div class="mt-2 h-2 bg-mushroom-100 dark:bg-mushroom-800 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-300"
            :class="budgetProgress > 100 ? 'bg-tomato-500' : budgetProgress > 80 ? 'bg-mango-500' : 'bg-kangkong-500'"
            :style="{ width: Math.min(budgetProgress, 100) + '%' }"
          ></div>
        </div>
        <div class="text-xs text-mushroom-400 dark:text-mushroom-500 mt-1">
          {{ currentMonthBudget ? `${currencySymbol}${currentMonthExpense.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / ${currencySymbol}${currentMonthBudget.total_budget.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'No budget set' }}
        </div>
      </div>

      <div class="card-elevated p-4">
        <div class="text-xs text-mushroom-400 dark:text-mushroom-500 mb-1">Expenses This Month</div>
        <div class="text-lg font-semibold text-tomato-500">
          {{ currencySymbol }}{{ currentMonthExpense.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
        </div>
        <div class="text-xs text-mushroom-400 dark:text-mushroom-500 mt-1">
          {{ new Date().toLocaleString('en-US', { month: 'long' }) }} {{ currentYear }}
        </div>
      </div>

      <div class="card-elevated p-4">
        <div class="text-xs text-mushroom-400 dark:text-mushroom-500 mb-1">Income This Month</div>
        <div class="text-lg font-semibold text-kangkong-500">
          {{ currencySymbol }}{{ currentMonthIncome.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
        </div>
        <div class="text-xs text-mushroom-400 dark:text-mushroom-500 mt-1">
          {{ new Date().toLocaleString('en-US', { month: 'long' }) }} {{ currentYear }}
        </div>
      </div>
    </div>

    <div v-if="summary" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="card-elevated p-4 -mb-2">
        <h3 class="text-sm font-medium text-mushroom-600 dark:text-mushroom-400 mb-2">Monthly Trend</h3>
        <div class="h-48">
          <Line ref="trendChartRef" :data="monthlyChartData" :options="trendLineOpts" />
        </div>
        <div class="flex items-center justify-center gap-4 mt-2">
          <button
            @click="toggleIncome"
            class="flex items-center gap-1.5 text-xs transition-opacity"
            :class="incomeVisible ? 'opacity-100 font-medium text-mushroom-700 dark:text-mushroom-300' : 'opacity-40 text-mushroom-500 dark:text-mushroom-400'"
          >
            <span class="w-2.5 h-2.5 rounded-full bg-kangkong-500"></span>
            Income
          </button>
          <button
            @click="toggleExpenses"
            class="flex items-center gap-1.5 text-xs transition-opacity"
            :class="expensesVisible ? 'opacity-100 font-medium text-mushroom-700 dark:text-mushroom-300' : 'opacity-40 text-mushroom-500 dark:text-mushroom-400'"
          >
            <span class="w-2.5 h-2.5 rounded-full bg-tomato-500"></span>
            Expenses
          </button>
        </div>
      </div>

      <div class="card-elevated p-4 -mb-2">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-sm font-medium text-mushroom-600 dark:text-mushroom-400">
            {{ drilledGroup ? drilledGroup : 'Expense by Group' }}
          </h3>
          <div class="flex items-center gap-2">
            <button v-if="drilledGroup" @click="drilledGroup = null" class="text-xs text-kangkong-600 hover:text-kangkong-700 font-medium whitespace-nowrap">
              ← Back
            </button>
            <select v-model="selectedMonth" class="select-field text-xs py-1 px-2 min-w-[70px]">
              <option v-for="m in pieMonths" :key="m.value" :value="m.value">{{ m.label }}</option>
            </select>
            <select v-model="pieYear" class="select-field text-xs py-1 px-2 min-w-[60px]">
              <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
            </select>
          </div>
        </div>
        <div class="h-48">
          <Doughnut
            v-if="!drilledGroup"
            :data="groupChartData"
            :options="{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 8, font: { size: 10 } } }, tooltip: { callbacks: { label: pctTooltip } }, cutout: '55%' }, onClick: (e, el) => { if (el.length) { drilledGroup = groupChartData.labels[el[0].index] } } }"
            :style="{ cursor: 'pointer' }"
          />
          <Doughnut
            v-else
            :data="drilledChartData"
            :options="doughnutOpts"
            :style="{ cursor: 'pointer' }"
          />
        </div>
      </div>
    </div>

    <div class="card-elevated p-4">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-3">
          <h3 class="text-sm font-medium text-mushroom-600 dark:text-mushroom-400">Income Breakdown</h3>
          <div class="flex bg-mushroom-100 dark:bg-mushroom-800 rounded-md p-0.5">
            <button @click="incomeMatrixMode = 'category'" class="px-2 py-0.5 text-xs rounded" :class="incomeMatrixMode === 'category' ? 'bg-white dark:bg-mushroom-900 text-mushroom-900 dark:text-mushroom-50 shadow-sm' : 'text-mushroom-500 dark:text-mushroom-400'">Categories</button>
            <button @click="incomeMatrixMode = 'account'" class="px-2 py-0.5 text-xs rounded" :class="incomeMatrixMode === 'account' ? 'bg-white dark:bg-mushroom-900 text-mushroom-900 dark:text-mushroom-50 shadow-sm' : 'text-mushroom-500 dark:text-mushroom-400'">Accounts</button>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <select v-model="selectedYear" class="select-field text-xs py-1 px-2 w-auto">
            <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
          </select>
          <label class="flex items-center gap-1 text-xs text-mushroom-500 dark:text-mushroom-400 cursor-pointer">
            <input type="checkbox" v-model="showAverages" class="rounded" />
            Show Averages
          </label>
        </div>
      </div>

      <div v-if="incomeMatrixMode === 'category'" class="overflow-x-auto">
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-mushroom-200 dark:border-mushroom-700">
              <th class="text-left px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400 sticky left-0 bg-white dark:bg-mushroom-900">Category</th>
              <th v-for="(m, i) in incomeMatrixMonths" :key="i" class="text-right px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">{{ m }}</th>
              <th class="text-right px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400 border-l border-mushroom-200 dark:border-mushroom-700">Total {{ currencySymbol }}</th>
              <th v-if="showAverages" class="text-right px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400 border-l border-mushroom-200 dark:border-mushroom-700">Avg {{ currencySymbol }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in incomeMatrixRows" :key="row.name" class="border-b border-mushroom-100 dark:border-mushroom-700/50">
              <td class="px-2 py-1 text-mushroom-600 dark:text-mushroom-400 sticky left-0 bg-white dark:bg-mushroom-900">{{ row.name }}</td>
              <td v-for="(val, i) in row.data" :key="i" class="text-right px-2 py-1 text-mushroom-700 dark:text-mushroom-300">{{ formatConverted(val) }}</td>
              <td class="text-right px-2 py-1 font-medium text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(row.data.reduce((a, b) => a + b, 0)) }}</td>
              <td v-if="showAverages" class="text-right px-2 py-1 text-mushroom-500 dark:text-mushroom-400 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(Math.round(row.data.reduce((a, b) => a + b, 0) / 12)) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="border-t-2 border-mushroom-300 dark:border-mushroom-600 font-medium">
              <td class="px-2 py-1.5 text-mushroom-950 dark:text-mushroom-50 sticky left-0 bg-white dark:bg-mushroom-900">Total</td>
              <td v-for="(val, i) in incomeMatrixMonthlyTotals" :key="i" class="text-right px-2 py-1.5 text-mushroom-950 dark:text-mushroom-50">{{ formatConverted(val) }}</td>
              <td class="text-right px-2 py-1.5 font-semibold text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(incomeMatrixGrandTotal) }}</td>
              <td v-if="showAverages" class="text-right px-2 py-1.5 text-mushroom-600 dark:text-mushroom-400 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(incomeMatrixAvg) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-mushroom-200 dark:border-mushroom-700">
              <th class="text-left px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400 sticky left-0 bg-white dark:bg-mushroom-900">Account</th>
              <th v-for="(m, i) in incomeMatrixMonths" :key="i" class="text-right px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">{{ m }}</th>
              <th class="text-right px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400 border-l border-mushroom-200 dark:border-mushroom-700">Total {{ currencySymbol }}</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in incomeAccountRows" :key="row.name + row.type">
              <tr
                v-if="row.type === 'group'"
                class="bg-mushroom-50 dark:bg-mushroom-800 cursor-pointer select-none hover:bg-mushroom-100 dark:hover:bg-mushroom-700 transition-colors"
                @click="toggleIncomeAccountCollapse(row.name)"
              >
                <td class="px-2 py-1 font-medium text-mushroom-700 dark:text-mushroom-300">
                  <span class="inline-flex items-center gap-1">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="transition-transform duration-200" :class="isIncomeAccountCollapsed(row.name) ? '' : 'rotate-90'">
                      <path d="M9 5l7 7-7 7"/>
                    </svg>
                    {{ row.name.replace('_', ' ') }}
                  </span>
                </td>
                <template v-if="isIncomeAccountCollapsed(row.name)">
                  <td v-for="(val, i) in (incomeAccountRows.find(r => r.type === 'groupTotal' && r.name === row.name) || {}).data || []" :key="i" class="text-right px-2 py-1 font-medium text-mushroom-700 dark:text-mushroom-300">{{ formatConverted(val) }}</td>
                  <td class="text-right px-2 py-1 font-semibold text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(((incomeAccountRows.find(r => r.type === 'groupTotal' && r.name === row.name) || {}).data || []).reduce((a, b) => a + b, 0)) }}</td>
                </template>
                <td v-else :colspan="13"></td>
              </tr>
              <tr v-else-if="row.type === 'account' && !isIncomeAccountCollapsed(row.group)" class="border-b border-mushroom-100 dark:border-mushroom-700/50">
                <td class="px-2 py-1 text-mushroom-600 dark:text-mushroom-400 sticky left-0 bg-white dark:bg-mushroom-900 pl-6">{{ row.name }}</td>
                <td v-for="(val, i) in row.data" :key="i" class="text-right px-2 py-1 text-mushroom-700 dark:text-mushroom-300">{{ formatConverted(val) }}</td>
                <td class="text-right px-2 py-1 font-medium text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(row.data.reduce((a, b) => a + b, 0)) }}</td>
              </tr>
              <tr v-else-if="row.type === 'groupTotal' && !isIncomeAccountCollapsed(row.name)" class="bg-mushroom-50 dark:bg-mushroom-800 border-b border-mushroom-200 dark:border-mushroom-700">
                <td class="px-2 py-1 font-medium text-mushroom-700 dark:text-mushroom-300 sticky left-0 bg-mushroom-50 dark:bg-mushroom-800 pl-6">{{ row.name.replace('_', ' ') }} Total</td>
                <td v-for="(val, i) in row.data" :key="i" class="text-right px-2 py-1 font-medium text-mushroom-700 dark:text-mushroom-300">{{ formatConverted(val) }}</td>
                <td class="text-right px-2 py-1 font-semibold text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(row.data.reduce((a, b) => a + b, 0)) }}</td>
              </tr>
            </template>
          </tbody>
          <tfoot>
            <tr class="border-t-2 border-mushroom-300 dark:border-mushroom-600 font-medium">
              <td class="px-2 py-1.5 text-mushroom-950 dark:text-mushroom-50 sticky left-0 bg-white dark:bg-mushroom-900">Total</td>
              <td v-for="(val, i) in incomeAccountMonthlyTotals" :key="i" class="text-right px-2 py-1.5 text-mushroom-950 dark:text-mushroom-50">{{ formatConverted(val) }}</td>
              <td class="text-right px-2 py-1.5 font-semibold text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(incomeAccountGrandTotal) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>

    <div class="card-elevated p-4">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-3">
          <h3 class="text-sm font-medium text-mushroom-600 dark:text-mushroom-400">Expense Breakdown</h3>
          <div class="flex bg-mushroom-100 dark:bg-mushroom-800 rounded-md p-0.5">
            <button @click="expenseMatrixMode = 'category'" class="px-2 py-0.5 text-xs rounded" :class="expenseMatrixMode === 'category' ? 'bg-white dark:bg-mushroom-900 text-mushroom-900 dark:text-mushroom-50 shadow-sm' : 'text-mushroom-500 dark:text-mushroom-400'">Categories</button>
            <button @click="expenseMatrixMode = 'account'" class="px-2 py-0.5 text-xs rounded" :class="expenseMatrixMode === 'account' ? 'bg-white dark:bg-mushroom-900 text-mushroom-900 dark:text-mushroom-50 shadow-sm' : 'text-mushroom-500 dark:text-mushroom-400'">Accounts</button>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <select v-model="selectedYear" class="select-field text-xs py-1 px-2 w-auto">
            <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
          </select>
          <label class="flex items-center gap-1 text-xs text-mushroom-500 dark:text-mushroom-400 cursor-pointer">
            <input type="checkbox" v-model="showAverages" class="rounded" />
            Show Averages
          </label>
        </div>
      </div>

      <div v-if="expenseMatrixMode === 'category'" class="overflow-x-auto">
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-mushroom-200 dark:border-mushroom-700">
              <th class="text-left px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400 sticky left-0 bg-white dark:bg-mushroom-900">Category</th>
              <th v-for="(m, i) in matrixMonths" :key="i" class="text-right px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">{{ m }}</th>
              <th class="text-right px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400 border-l border-mushroom-200 dark:border-mushroom-700">Total {{ currencySymbol }}</th>
              <th v-if="showAverages" class="text-right px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400 border-l border-mushroom-200 dark:border-mushroom-700">Avg {{ currencySymbol }}</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in matrixRows" :key="row.name + row.type">
              <tr
                v-if="row.type === 'group'"
                class="bg-mushroom-50 dark:bg-mushroom-800 cursor-pointer select-none hover:bg-mushroom-100 dark:hover:bg-mushroom-700 transition-colors"
                @click="toggleGroupCollapse(row.name)"
              >
                <td class="px-2 py-1 font-medium text-mushroom-700 dark:text-mushroom-300">
                  <span class="inline-flex items-center gap-1">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="transition-transform duration-200" :class="isGroupCollapsed(row.name) ? '' : 'rotate-90'">
                      <path d="M9 5l7 7-7 7"/>
                    </svg>
                    {{ row.name }}
                  </span>
                </td>
                <template v-if="isGroupCollapsed(row.name)">
                  <td v-for="(val, i) in (matrixRows.find(r => r.type === 'groupTotal' && r.name === row.name) || {}).data || []" :key="i" class="text-right px-2 py-1 font-medium text-mushroom-700 dark:text-mushroom-300">{{ formatConverted(val) }}</td>
                  <td class="text-right px-2 py-1 font-semibold text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(((matrixRows.find(r => r.type === 'groupTotal' && r.name === row.name) || {}).data || []).reduce((a, b) => a + b, 0)) }}</td>
                  <td v-if="showAverages" class="text-right px-2 py-1 text-mushroom-600 dark:text-mushroom-400 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(Math.round(((matrixRows.find(r => r.type === 'groupTotal' && r.name === row.name) || {}).data || []).reduce((a, b) => a + b, 0) / 12)) }}</td>
                </template>
                <td v-else :colspan="13"></td>
              </tr>
              <tr v-else-if="row.type === 'category' && !isGroupCollapsed(row.group)" class="border-b border-mushroom-100 dark:border-mushroom-700/50">
                <td class="px-2 py-1 text-mushroom-600 dark:text-mushroom-400 sticky left-0 bg-white dark:bg-mushroom-900 pl-6">{{ row.name }}</td>
                <td v-for="(val, i) in row.data" :key="i" class="text-right px-2 py-1 text-mushroom-700 dark:text-mushroom-300">{{ formatConverted(val) }}</td>
                <td class="text-right px-2 py-1 font-medium text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(row.data.reduce((a, b) => a + b, 0)) }}</td>
                <td v-if="showAverages" class="text-right px-2 py-1 text-mushroom-500 dark:text-mushroom-400 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(Math.round(row.data.reduce((a, b) => a + b, 0) / 12)) }}</td>
              </tr>
              <tr v-else-if="row.type === 'groupTotal' && !isGroupCollapsed(row.name)" class="bg-mushroom-50 dark:bg-mushroom-800 border-b border-mushroom-200 dark:border-mushroom-700">
                <td class="px-2 py-1 font-medium text-mushroom-700 dark:text-mushroom-300 sticky left-0 bg-mushroom-50 dark:bg-mushroom-800 pl-6">{{ row.name }} Total</td>
                <td v-for="(val, i) in row.data" :key="i" class="text-right px-2 py-1 font-medium text-mushroom-700 dark:text-mushroom-300">{{ formatConverted(val) }}</td>
                <td class="text-right px-2 py-1 font-semibold text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(row.data.reduce((a, b) => a + b, 0)) }}</td>
                <td v-if="showAverages" class="text-right px-2 py-1 text-mushroom-600 dark:text-mushroom-400 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(Math.round(row.data.reduce((a, b) => a + b, 0) / 12)) }}</td>
              </tr>
            </template>
          </tbody>
          <tfoot>
            <tr class="border-t-2 border-mushroom-300 dark:border-mushroom-600 font-medium">
              <td class="px-2 py-1.5 text-mushroom-950 dark:text-mushroom-50 sticky left-0 bg-white dark:bg-mushroom-900">Total</td>
              <td v-for="(val, i) in matrixMonthlyTotals" :key="i" class="text-right px-2 py-1.5 text-mushroom-950 dark:text-mushroom-50">{{ formatConverted(val) }}</td>
              <td class="text-right px-2 py-1.5 font-semibold text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(matrixGrandTotal) }}</td>
              <td v-if="showAverages" class="text-right px-2 py-1.5 text-mushroom-600 dark:text-mushroom-400 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(matrixAvg) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-mushroom-200 dark:border-mushroom-700">
              <th class="text-left px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400 sticky left-0 bg-white dark:bg-mushroom-900">Account</th>
              <th v-for="(m, i) in matrixMonths" :key="i" class="text-right px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">{{ m }}</th>
              <th class="text-right px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400 border-l border-mushroom-200 dark:border-mushroom-700">Total {{ currencySymbol }}</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in expenseAccountRows" :key="row.name + row.type">
              <tr
                v-if="row.type === 'group'"
                class="bg-mushroom-50 dark:bg-mushroom-800 cursor-pointer select-none hover:bg-mushroom-100 dark:hover:bg-mushroom-700 transition-colors"
                @click="toggleExpenseAccountCollapse(row.name)"
              >
                <td class="px-2 py-1 font-medium text-mushroom-700 dark:text-mushroom-300">
                  <span class="inline-flex items-center gap-1">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="transition-transform duration-200" :class="isExpenseAccountCollapsed(row.name) ? '' : 'rotate-90'">
                      <path d="M9 5l7 7-7 7"/>
                    </svg>
                    {{ row.name.replace('_', ' ') }}
                  </span>
                </td>
                <template v-if="isExpenseAccountCollapsed(row.name)">
                  <td v-for="(val, i) in (expenseAccountRows.find(r => r.type === 'groupTotal' && r.name === row.name) || {}).data || []" :key="i" class="text-right px-2 py-1 font-medium text-mushroom-700 dark:text-mushroom-300">{{ formatConverted(val) }}</td>
                  <td class="text-right px-2 py-1 font-semibold text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(((expenseAccountRows.find(r => r.type === 'groupTotal' && r.name === row.name) || {}).data || []).reduce((a, b) => a + b, 0)) }}</td>
                </template>
                <td v-else :colspan="13"></td>
              </tr>
              <tr v-else-if="row.type === 'account' && !isExpenseAccountCollapsed(row.group)" class="border-b border-mushroom-100 dark:border-mushroom-700/50">
                <td class="px-2 py-1 text-mushroom-600 dark:text-mushroom-400 sticky left-0 bg-white dark:bg-mushroom-900 pl-6">{{ row.name }}</td>
                <td v-for="(val, i) in row.data" :key="i" class="text-right px-2 py-1 text-mushroom-700 dark:text-mushroom-300">{{ formatConverted(val) }}</td>
                <td class="text-right px-2 py-1 font-medium text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(row.data.reduce((a, b) => a + b, 0)) }}</td>
              </tr>
              <tr v-else-if="row.type === 'groupTotal' && !isExpenseAccountCollapsed(row.name)" class="bg-mushroom-50 dark:bg-mushroom-800 border-b border-mushroom-200 dark:border-mushroom-700">
                <td class="px-2 py-1 font-medium text-mushroom-700 dark:text-mushroom-300 sticky left-0 bg-mushroom-50 dark:bg-mushroom-800 pl-6">{{ row.name.replace('_', ' ') }} Total</td>
                <td v-for="(val, i) in row.data" :key="i" class="text-right px-2 py-1 font-medium text-mushroom-700 dark:text-mushroom-300">{{ formatConverted(val) }}</td>
                <td class="text-right px-2 py-1 font-semibold text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(row.data.reduce((a, b) => a + b, 0)) }}</td>
              </tr>
            </template>
          </tbody>
          <tfoot>
            <tr class="border-t-2 border-mushroom-300 dark:border-mushroom-600 font-medium">
              <td class="px-2 py-1.5 text-mushroom-950 dark:text-mushroom-50 sticky left-0 bg-white dark:bg-mushroom-900">Total</td>
              <td v-for="(val, i) in expenseAccountMonthlyTotals" :key="i" class="text-right px-2 py-1.5 text-mushroom-950 dark:text-mushroom-50">{{ formatConverted(val) }}</td>
              <td class="text-right px-2 py-1.5 font-semibold text-mushroom-950 dark:text-mushroom-50 border-l border-mushroom-200 dark:border-mushroom-700">{{ formatConverted(expenseAccountGrandTotal) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
    </template>
  </div>
</template>
