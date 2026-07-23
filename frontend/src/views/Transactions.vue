<script setup>
import { ref, onMounted, computed } from 'vue'
import { useTransactions } from '../composables/useTransactions'
import { useAccounts } from '../composables/useAccounts'
import CategoryBadge from '../components/CategoryBadge.vue'
import api from '../api'

const { transactions, loading, fetchTransactions, deleteTransaction } = useTransactions()
const { accounts, fetchAccounts } = useAccounts()

const filters = ref({ account_id: '', category: '', start_date: '', end_date: '' })
const categories = ref([])

onMounted(async () => {
  await Promise.all([fetchTransactions(), fetchAccounts(), fetchCategories()])
})

async function fetchCategories() {
  const { data } = await api.get('/categories')
  categories.value = data
}

const categoryToGroup = computed(() => {
  const map = {}
  for (const c of categories.value) {
    map[c.name] = c.group
  }
  return map
})

async function applyFilters() {
  const f = {}
  if (filters.value.account_id) f.account_id = filters.value.account_id
  if (filters.value.category) f.category = filters.value.category
  if (filters.value.start_date) f.start_date = filters.value.start_date
  if (filters.value.end_date) f.end_date = filters.value.end_date
  await fetchTransactions(f)
}

async function handleDelete(id) {
  if (confirm('Delete this transaction?')) {
    await deleteTransaction(id)
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
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}
</script>

<template>
  <div class="space-y-4">
    <h2 class="text-2xl font-extrabold text-charcoal">Transactions</h2>

    <div class="card p-4 flex flex-wrap gap-3">
      <select v-model="filters.account_id" class="select-field w-auto min-w-[160px]">
        <option value="">All accounts</option>
        <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
      <input v-model="filters.category" placeholder="Category" class="input-field w-auto min-w-[140px]" />
      <input v-model="filters.start_date" type="date" class="input-field w-auto" />
      <input v-model="filters.end_date" type="date" class="input-field w-auto" />
      <button @click="applyFilters" class="btn-primary text-sm">Filter</button>
    </div>

    <div v-if="loading" class="text-center text-charcoal-light py-8 font-semibold">Loading...</div>

    <div v-else class="space-y-4">
      <div v-for="[date, txns] in groupedByDate(transactions)" :key="date" class="card overflow-hidden">
        <div class="px-4 py-2.5 bg-cream/50 border-b border-cream-dark">
          <span class="text-sm font-bold text-charcoal-light">{{ formatDate(date) }}</span>
        </div>
        <div v-for="t in txns" :key="t.id" class="flex items-center justify-between px-4 py-3 border-b border-cream-dark last:border-0 hover:bg-cream/30 transition-colors">
          <div class="flex items-center gap-3">
            <CategoryBadge :name="t.category" :group="categoryToGroup[t.category]" />
            <div>
              <div class="text-sm font-semibold text-charcoal">{{ t.description || t.category }}</div>
              <div class="text-xs text-charcoal-light">{{ accounts.find(a => a.id === t.account_id)?.name || t.account_id }}</div>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="font-extrabold text-sm" :class="t.type === 'income' ? 'text-sage-dark' : 'text-coral'">
              {{ t.type === 'income' ? '+' : '-' }}{{ t.currency }} {{ t.amount.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}
            </span>
            <router-link :to="`/transactions/${t.id}/edit`" class="text-coral hover:text-coral-dark text-xs font-bold">Edit</router-link>
            <button @click="handleDelete(t.id)" class="text-charcoal-light hover:text-coral text-xs font-bold">Del</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
