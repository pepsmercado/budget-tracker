<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import { useTransactions } from '../composables/useTransactions'
import { useAccounts } from '../composables/useAccounts'
import Skeleton from '../components/Skeleton.vue'

const props = defineProps({ currency: { type: String, default: 'php' } })

const route = useRoute()
const router = useRouter()
const { createTransaction, updateTransaction } = useTransactions()
const { accounts, fetchAccounts } = useAccounts()

const currencyParam = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')

const categories = ref([])
const isEdit = computed(() => !!route.params.id)
const loading = ref(false)
const pageLoading = ref(true)

const currencyAccounts = computed(() => {
  return accounts.value.filter(a => a.currency === currencyParam.value)
})

const groupedAccounts = computed(() => {
  const groups = {}
  for (const a of currencyAccounts.value) {
    if (!groups[a.type]) groups[a.type] = []
    groups[a.type].push(a)
  }
  return groups
})

const groupedCategories = computed(() => {
  const groups = {}
  const filtered = categories.value.filter(c => c.type === form.value.type)
  for (const c of filtered) {
    const group = c.group
    if (!groups[group]) groups[group] = []
    groups[group].push(c)
  }
  const order = ['Income', 'Fixed', 'Essential', 'Lifestyle', 'School', 'Misc', 'Sinking']
  const sorted = {}
  for (const g of order) {
    if (groups[g]) sorted[g] = groups[g]
  }
  return sorted
})

const form = ref({
  date: new Date().toISOString().split('T')[0],
  account_id: '',
  type: 'expense',
  amount: '',
  currency: currencyParam.value,
  category: '',
  description: '',
  sub_account_id: '',
})

const selectedAccount = computed(() => accounts.value.find(a => a.id === form.value.account_id))
const isInvestment = computed(() => selectedAccount.value?.type === 'investment')

function onAccountChange() {
  const acc = accounts.value.find(a => a.id === form.value.account_id)
  if (acc) {
    form.value.currency = acc.currency
    form.value.sub_account_id = ''
  }
}

onMounted(async () => {
  await Promise.all([fetchAccounts(), fetchCategories()])
  pageLoading.value = false
  if (isEdit.value) {
    const { data: txns } = await api.get('/transactions')
    const t = txns.find(x => x.id === route.params.id)
    if (t) {
      form.value = {
        date: t.date,
        account_id: t.account_id,
        type: t.type,
        amount: t.amount,
        currency: t.currency,
        category: t.category,
        description: t.description,
        sub_account_id: t.sub_account_id || '',
      }
    }
  }
})

async function fetchCategories() {
  const { data } = await api.get('/categories')
  categories.value = data
}

async function handleSubmit() {
  loading.value = true
  try {
    const payload = { ...form.value, amount: parseFloat(form.value.amount) }
    if (isEdit.value) {
      await updateTransaction(route.params.id, payload)
    } else {
      await createTransaction(payload)
    }
    router.push(`/${props.currency}/transactions`)
  } catch (e) {
    console.error('Failed to save transaction:', e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-lg">
    <h2 class="text-lg font-medium text-mushroom-950 dark:text-mushroom-50 mb-4">{{ isEdit ? 'Edit' : 'New' }} Transaction</h2>

    <!-- Skeleton loading -->
    <div v-if="pageLoading" class="card-elevated p-5 space-y-4">
      <Skeleton width="120px" height="16px" class="mb-3" />
      <Skeleton width="100%" height="40px" rounded="rounded-lg" />
      <Skeleton width="100%" height="40px" rounded="rounded-lg" />
      <Skeleton width="100%" height="40px" rounded="rounded-lg" />
      <div class="grid grid-cols-2 gap-3">
        <Skeleton width="100%" height="40px" rounded="rounded-lg" />
        <Skeleton width="100%" height="40px" rounded="rounded-lg" />
      </div>
      <Skeleton width="100%" height="40px" rounded="rounded-lg" />
      <Skeleton width="100%" height="40px" rounded="rounded-lg" />
      <div class="flex gap-2 pt-1">
        <Skeleton width="80px" height="36px" rounded="rounded-lg" />
        <Skeleton width="60px" height="36px" rounded="rounded-lg" />
      </div>
    </div>

    <form v-else @submit.prevent="handleSubmit" class="card-elevated p-5 space-y-4">
      <div>
        <label class="label-text">Date</label>
        <input v-model="form.date" type="date" required class="input-field" />
      </div>

      <div>
        <label class="label-text">Account</label>
        <select v-model="form.account_id" @change="onAccountChange" required class="select-field">
          <option value="" disabled>Select account</option>
          <template v-for="(accs, type) in groupedAccounts" :key="type">
            <optgroup :label="type.replace('_', ' ')">
              <option v-for="a in accs" :key="a.id" :value="a.id">{{ a.name }}</option>
            </optgroup>
          </template>
        </select>
      </div>

      <div v-if="isInvestment && selectedAccount?.sub_accounts?.length">
        <label class="label-text">Investment Type</label>
        <select v-model="form.sub_account_id" class="select-field">
          <option value="">Select type</option>
          <option v-for="sub in selectedAccount.sub_accounts" :key="sub.id" :value="sub.id">{{ sub.name }}</option>
        </select>
      </div>

      <div>
        <label class="label-text">Type</label>
          <select v-model="form.type" class="select-field">
            <option value="expense">Expense</option>
            <option value="income">Income</option>
          </select>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="label-text">Amount</label>
          <input v-model="form.amount" type="number" step="0.01" min="0.01" required class="input-field" />
        </div>
        <div>
          <label class="label-text">Currency</label>
          <input :value="currencyParam" disabled class="input-field bg-mushroom-50 dark:bg-mushroom-800" />
        </div>
      </div>

      <div>
        <label class="label-text">Category</label>
        <select v-model="form.category" required class="select-field">
          <option value="" disabled>Select category</option>
          <template v-for="(cats, group) in groupedCategories" :key="group">
            <optgroup :label="group">
              <option v-for="c in cats" :key="c.id" :value="c.name">{{ c.name }}</option>
            </optgroup>
          </template>
        </select>
      </div>

      <div>
        <label class="label-text">Description</label>
        <input v-model="form.description" class="input-field" placeholder="Optional note" />
      </div>

      <div class="flex gap-2 pt-1">
        <button type="submit" :disabled="loading" class="btn-primary disabled:opacity-50">
          {{ loading ? 'Saving...' : 'Save' }}
        </button>
        <router-link :to="`/${props.currency}/transactions`" class="btn-ghost">Cancel</router-link>
      </div>
    </form>
  </div>
</template>
