<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import { useTransactions } from '../composables/useTransactions'
import { useAccounts } from '../composables/useAccounts'

const route = useRoute()
const router = useRouter()
const { createTransaction, updateTransaction, fetchTransactions } = useTransactions()
const { accounts, fetchAccounts } = useAccounts()

const categories = ref([])
const isEdit = computed(() => !!route.params.id)
const loading = ref(false)

const form = ref({
  date: new Date().toISOString().split('T')[0],
  account_id: '',
  type: 'expense',
  amount: '',
  currency: 'PHP',
  category: '',
  description: '',
})

onMounted(async () => {
  await Promise.all([fetchAccounts(), fetchCategories()])
  if (isEdit.value) {
    await fetchTransactions()
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
    router.push('/transactions')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-lg">
    <h2 class="text-2xl font-extrabold text-charcoal mb-6">{{ isEdit ? 'Edit' : 'New' }} Transaction</h2>

    <form @submit.prevent="handleSubmit" class="card-elevated p-6 space-y-4">
      <div>
        <label class="label-text">Date</label>
        <input v-model="form.date" type="date" required class="input-field" />
      </div>

      <div>
        <label class="label-text">Account</label>
        <select v-model="form.account_id" required class="select-field">
          <option value="" disabled>Select account</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }} ({{ a.currency }})</option>
        </select>
      </div>

      <div>
        <label class="label-text">Type</label>
        <select v-model="form.type" class="select-field">
          <option value="expense">Expense</option>
          <option value="income">Income</option>
          <option value="transfer">Transfer</option>
        </select>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="label-text">Amount</label>
          <input v-model="form.amount" type="number" step="0.01" min="0.01" required class="input-field" />
        </div>
        <div>
          <label class="label-text">Currency</label>
          <input v-model="form.currency" maxlength="3" required class="input-field" />
        </div>
      </div>

      <div>
        <label class="label-text">Category</label>
        <select v-model="form.category" required class="select-field">
          <option value="" disabled>Select category</option>
          <option v-for="c in categories.filter(c => c.type === form.type)" :key="c.id" :value="c.name">{{ c.name }}</option>
        </select>
      </div>

      <div>
        <label class="label-text">Description</label>
        <input v-model="form.description" class="input-field" placeholder="Optional note" />
      </div>

      <div class="flex gap-3 pt-2">
        <button type="submit" :disabled="loading" class="btn-primary disabled:opacity-50">
          {{ loading ? 'Saving...' : 'Save' }}
        </button>
        <router-link to="/transactions" class="btn-ghost">Cancel</router-link>
      </div>
    </form>
  </div>
</template>
