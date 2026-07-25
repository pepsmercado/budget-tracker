<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useTransactions } from '../composables/useTransactions'
import { useAccounts } from '../composables/useAccounts'
import CategoryBadge from '../components/CategoryBadge.vue'
import Skeleton from '../components/Skeleton.vue'
import { categoryIcons } from '../constants.js'
import { useToast } from '../composables/useToast.js'
import api from '../api'

const loadingPage = ref(true)
const confirmingDelete = ref(null)

const props = defineProps({ currency: { type: String, default: 'php' } })

const { transactions, loading, fetchTransactions, deleteTransaction } = useTransactions()
const { accounts, fetchAccounts } = useAccounts()
const toast = useToast()

const currencyParam = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')
const currencySymbol = computed(() => props.currency === 'usd' ? '$' : '₱')
const viewLabel = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')

const filters = ref({ account_id: '', type: '', group: '', category: '', start_date: '', end_date: '' })
const hideTransfers = ref(localStorage.getItem(`transactions-hide-transfers-${currencyParam.value}`) !== 'false')
const categories = ref([])

async function loadAll() {
  await Promise.all([fetchTransactions({ currency: currencyParam.value }), fetchAccounts(), fetchCategories()])
  loadingPage.value = false
}

onMounted(loadAll)

watch(currencyParam, () => {
  filters.value = { account_id: '', type: '', group: '', category: '', start_date: '', end_date: '' }
  loadAll()
})

async function fetchCategories() {
  const { data } = await api.get('/categories')
  categories.value = data
}

const filteredCategories = computed(() => {
  if (!filters.value.type) return categories.value
  return categories.value.filter(c => c.type === filters.value.type)
})

const categoryToGroup = computed(() => {
  const map = {}
  for (const c of categories.value) {
    map[c.name] = c.group
  }
  return map
})

const currencyAccounts = computed(() => {
  return accounts.value.filter(a => a.currency === currencyParam.value)
})

const groupedAccounts = computed(() => {
  const groups = {}
  for (const acc of currencyAccounts.value) {
    const type = acc.type
    if (!groups[type]) groups[type] = []
    groups[type].push(acc)
  }
  return groups
})

const filteredGroups = computed(() => {
  const groups = {}
  for (const c of filteredCategories.value) {
    const group = c.group
    if (!groups[group]) groups[group] = []
    groups[group].push(c)
  }
  return groups
})

const groupedCategories = computed(() => {
  if (filters.value.group && filteredGroups.value[filters.value.group]) {
    return { [filters.value.group]: filteredGroups.value[filters.value.group] }
  }
  return filteredGroups.value
})

const groupNames = computed(() => Object.keys(groupedCategories.value))

watch(() => filters.value.type, () => {
  filters.value.group = ''
  filters.value.category = ''
})

watch(() => filters.value.group, () => {
  filters.value.category = ''
})

watch(filters, () => {
  applyFilters()
}, { deep: true })

function clearFilters() {
  filters.value = { account_id: '', type: '', group: '', category: '', start_date: '', end_date: '' }
}

function toggleHideTransfers() {
  hideTransfers.value = !hideTransfers.value
  localStorage.setItem(`transactions-hide-transfers-${currencyParam.value}`, hideTransfers.value)
}

const displayTransactions = computed(() => {
  if (hideTransfers.value) {
    return transactions.value.filter(t => !t.transfer_pair_id)
  }
  return transactions.value
})

async function applyFilters() {
  const f = { currency: currencyParam.value }
  if (filters.value.account_id) f.account_id = filters.value.account_id
  if (filters.value.type) f.type = filters.value.type
  if (filters.value.group) f.group = filters.value.group
  if (filters.value.category) f.category = filters.value.category
  if (filters.value.start_date) f.start_date = filters.value.start_date
  if (filters.value.end_date) f.end_date = filters.value.end_date
  await fetchTransactions(f)
}

async function handleDelete(id) {
  try {
    await deleteTransaction(id)
    confirmingDelete.value = null
    toast.success('Transaction deleted')
  } catch (e) {
    console.error('Failed to delete transaction:', e)
  }
}

function groupedByDate(txns) {
  const groups = {}
  for (const t of txns) {
    const d = t.date
    if (!groups[d]) groups[d] = []
    groups[d].push(t)
  }
  return Object.entries(groups).sort((a, b) => b[0].localeCompare(a[0]))
}

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
}

const filteredStats = computed(() => {
  const income = displayTransactions.value.filter(t => t.type === 'income').reduce((s, t) => s + t.amount, 0)
  const expense = displayTransactions.value.filter(t => t.type === 'expense').reduce((s, t) => s + t.amount, 0)
  return { income, expense, net: income - expense }
})

function exportCSV() {
  const headers = ['Date', 'Type', 'Category', 'Group', 'Account', 'Description', 'Amount', 'Currency']
  const rows = transactions.value.map(t => [
    t.date,
    t.type,
    t.category,
    categoryToGroup.value[t.category] || '',
    accounts.value.find(a => a.id === t.account_id)?.name || t.account_id,
    t.description || '',
    t.amount,
    t.currency
  ])
  const csv = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `transactions-${currencyParam.value}-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="space-y-4">
    <!-- Page Header Skeleton -->
    <div v-if="loadingPage" class="flex items-center justify-between">
      <Skeleton width="120px" height="24px" />
      <Skeleton width="80px" height="32px" rounded="rounded-lg" />
    </div>
    
    <!-- Page Header -->
    <div v-else class="flex items-center justify-between">
      <h2 class="text-lg font-medium text-mushroom-950 dark:text-mushroom-50">{{ viewLabel }} Transactions</h2>
      <button @click="exportCSV" class="px-3 py-1.5 text-xs bg-kangkong-600 text-white rounded-lg hover:bg-kangkong-700 transition-colors font-medium">Export CSV</button>
    </div>

    <!-- Filter Skeleton -->
    <div v-if="loadingPage" class="card p-4 space-y-3">
      <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Skeleton width="100%" height="40px" rounded="rounded-lg" />
        <Skeleton width="100%" height="40px" rounded="rounded-lg" />
        <Skeleton width="100%" height="40px" rounded="rounded-lg" />
        <Skeleton width="100%" height="40px" rounded="rounded-lg" />
        <Skeleton width="100%" height="40px" rounded="rounded-lg" />
      </div>
    </div>
    
    <!-- Filters -->
    <div v-else class="card p-3 flex flex-wrap items-center gap-2 text-xs overflow-x-auto">
      <select v-model="filters.account_id" class="select-field py-1 px-1.5 text-xs min-w-[120px] w-auto shrink-0">
        <option value="">All accounts</option>
        <template v-for="(accs, type) in groupedAccounts" :key="type">
          <optgroup :label="type.replace('_', ' ')">
            <option v-for="a in accs" :key="a.id" :value="a.id">{{ a.name }}</option>
          </optgroup>
        </template>
      </select>
      <select v-model="filters.type" class="select-field py-1 px-1.5 text-xs min-w-[80px] w-auto shrink-0">
        <option value="">All types</option>
        <option value="expense">Expense</option>
        <option value="income">Income</option>
      </select>
      <select v-model="filters.group" :disabled="!filters.type" class="select-field py-1 px-1.5 text-xs min-w-[80px] w-auto shrink-0" :class="!filters.type ? 'opacity-50 cursor-not-allowed' : ''">
        <option value="">All groups</option>
        <option v-for="g in groupNames" :key="g" :value="g">{{ g }}</option>
      </select>
      <select v-model="filters.category" :disabled="!filters.type || !filters.group" class="select-field py-1 px-1.5 text-xs min-w-[100px] w-auto shrink-0" :class="!filters.type || !filters.group ? 'opacity-50 cursor-not-allowed' : ''">
        <option value="">All categories</option>
        <optgroup v-for="(cats, group) in groupedCategories" :key="group" :label="group">
          <option v-for="c in cats" :key="c.id" :value="c.name">{{ c.name }}</option>
        </optgroup>
      </select>
      <input v-model="filters.start_date" type="date" class="input-field py-1 px-1.5 text-xs w-auto shrink-0" />
      <input v-model="filters.end_date" type="date" class="input-field py-1 px-1.5 text-xs w-auto shrink-0" />
      <button v-if="filters.account_id || filters.type || filters.group || filters.category || filters.start_date || filters.end_date" @click="clearFilters" class="px-2 py-1 text-xs text-mushroom-500 dark:text-mushroom-400 hover:text-tomato-600 dark:hover:text-tomato-400 transition-colors shrink-0">Clear Filters</button>
      <div class="ml-auto flex items-center gap-1.5 shrink-0">
        <button
          @click="toggleHideTransfers"
          class="relative w-8 h-4 rounded-full transition-colors"
          :class="hideTransfers ? 'bg-kangkong-500' : 'bg-mushroom-200 dark:bg-mushroom-700'"
          title="Toggle transfer visibility"
        >
          <span class="absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform" :class="hideTransfers ? 'translate-x-4' : ''" />
        </button>
        <span class="text-xs text-mushroom-500 dark:text-mushroom-400">Transfers</span>
      </div>
    </div>

    <!-- Skeleton loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="g in 3" :key="g" class="card overflow-hidden">
        <div class="px-4 py-2 bg-mushroom-50 dark:bg-mushroom-800 border-b border-mushroom-200 dark:border-mushroom-700">
          <Skeleton width="120px" height="12px" />
        </div>
        <div v-for="r in 4" :key="r" class="flex items-center px-4 py-3 border-b border-mushroom-100 dark:border-mushroom-700/50 last:border-0 gap-3">
          <Skeleton width="36px" height="36px" rounded="rounded-lg" />
          <div class="flex-1 space-y-1.5">
            <Skeleton width="60%" height="14px" />
            <Skeleton width="40%" height="10px" />
          </div>
          <Skeleton width="80px" height="14px" />
        </div>
      </div>
    </div>

    <div v-else class="space-y-3">
      <div v-for="[date, txns] in groupedByDate(displayTransactions)" :key="date" class="card overflow-hidden">
        <div class="px-4 py-2 bg-mushroom-50 dark:bg-mushroom-800 border-b border-mushroom-200 dark:border-mushroom-700">
          <span class="text-xs font-medium text-mushroom-500 dark:text-mushroom-400">{{ formatDate(date) }}</span>
        </div>
        <div v-for="t in txns" :key="t.id" class="flex items-center px-4 py-2.5 border-b border-mushroom-100 dark:border-mushroom-700/50 last:border-0">
          <div class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 text-base" :class="t.transfer_pair_id ? 'bg-blueberry-50 dark:bg-blueberry-500/15' : t.type === 'income' ? 'bg-kangkong-50 dark:bg-kangkong-500/15' : 'bg-mushroom-50 dark:bg-mushroom-800'">
            {{ t.transfer_pair_id ? '↗' : categoryIcons[t.category] || '📋' }}
          </div>
          <div class="flex-1 min-w-0 px-3">
            <div class="text-sm text-mushroom-950 dark:text-mushroom-50 truncate">{{ t.description || t.category }}</div>
            <div class="flex items-center gap-2 mt-0.5">
              <span v-if="t.transfer_pair_id" class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium bg-blueberry-100 text-blueberry-700 dark:bg-blueberry-500/15 dark:text-blueberry-400">Transfer</span>
              <CategoryBadge v-else :name="t.category" :group="categoryToGroup[t.category]" />
              <span class="text-xs text-mushroom-400 dark:text-mushroom-500">{{ accounts.find(a => a.id === t.account_id)?.name || '' }}</span>
            </div>
          </div>
          <div class="flex items-center gap-3 flex-shrink-0">
            <span class="text-sm font-medium w-28 text-right" :class="t.type === 'income' ? 'text-kangkong-700 dark:text-kangkong-400' : 'text-tomato-600 dark:text-tomato-400'">
              {{ t.type === 'income' ? '+' : '-' }}{{ currencySymbol }}{{ t.amount.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}
            </span>
            <div class="w-20 text-right">
              <router-link :to="`/${currency}/transactions/${t.id}/edit`" class="text-xs text-mushroom-400 dark:text-mushroom-500 hover:text-kangkong-600 dark:hover:text-kangkong-400">Edit</router-link>
              <template v-if="confirmingDelete === t.id">
                <span class="text-xs text-mushroom-400 dark:text-mushroom-500 mx-1">|</span>
                <button @click="handleDelete(t.id)" class="text-xs text-tomato-500 hover:text-tomato-700 font-medium">Yes</button>
                <button @click="confirmingDelete = null" class="text-xs text-mushroom-400 dark:text-mushroom-500 hover:text-mushroom-600 dark:hover:text-mushroom-300 ml-1">No</button>
              </template>
              <button v-else @click="confirmingDelete = t.id" class="text-xs text-mushroom-400 dark:text-mushroom-500 hover:text-tomato-600 dark:hover:text-tomato-400 ml-2">Del</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
