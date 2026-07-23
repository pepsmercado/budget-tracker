<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAccounts } from '../composables/useAccounts'
import { useSummary } from '../composables/useSummary'
import BudgetProgressBar from '../components/BudgetProgressBar.vue'

const { accounts, loading, fetchAccounts, createAccount, deleteAccount, updateAccount, updateAccountGoal } = useAccounts()
const { balances, fetchBalances } = useSummary()

const showForm = ref(false)
const form = ref({ name: '', type: 'savings', currency: 'PHP', initial_balance: 0 })
const eyeHidden = ref(false)
const editingGoal = ref(null)
const goalValue = ref(0)

const goalTypes = ['savings', 'time_deposit']

const accountTypeLabels = {
  savings: 'Savings',
  checking: 'Checking',
  time_deposit: 'Time Deposit',
  investment: 'Investment',
  credit_card: 'Credit Card',
}

const accountTypeColors = {
  savings: 'border-l-kangkong-500',
  checking: 'border-l-blueberry-500',
  time_deposit: 'border-l-mango-500',
  investment: 'border-l-ubas-500',
}

const currencyLabels = { USD: '🇺🇸 US Accounts', PHP: '🇵🇭 Philippine Accounts' }
const currencyOrder = ['USD', 'PHP']

const groupedAccounts = computed(() => {
  const groups = {}
  for (const acc of accounts.value) {
    const currency = acc.currency || 'PHP'
    if (!groups[currency]) groups[currency] = []
    groups[currency].push(acc)
  }
  const sorted = {}
  for (const curr of currencyOrder) {
    if (groups[curr]) sorted[curr] = groups[curr]
  }
  for (const curr of Object.keys(groups).sort()) {
    if (!sorted[curr]) sorted[curr] = groups[curr]
  }
  return sorted
})

function getBalance(accountId) {
  const b = balances.value.find(x => x.account_id === accountId)
  return b ? b.balance : 0
}

function formatCurrency(val, currency) {
  if (eyeHidden.value) return '***'
  if (currency === 'USD') return `$${val.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
  return `₱${val.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
}

function goalProgress(balance, goal) {
  if (!goal || goal <= 0) return 0
  return Math.min((balance / goal) * 100, 100)
}

function startEditGoal(acc) {
  editingGoal.value = acc.id
  goalValue.value = acc.goal_amount || 0
}

async function saveGoal(acc) {
  await updateAccountGoal(acc.id, goalValue.value)
  editingGoal.value = null
}

function cancelGoal() {
  editingGoal.value = null
}

onMounted(async () => {
  await Promise.all([fetchAccounts(), fetchBalances()])
})

async function handleCreate() {
  await createAccount(form.value)
  showForm.value = false
  form.value = { name: '', type: 'savings', currency: 'PHP', initial_balance: 0 }
  await fetchBalances()
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-medium text-mushroom-950">Savings Goals</h2>
      <div class="flex items-center gap-3">
        <button @click="eyeHidden = !eyeHidden" class="text-mushroom-400 hover:text-mushroom-600">
          <svg v-if="!eyeHidden" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
        </button>
        <button @click="showForm = !showForm" class="btn-primary text-xs">
          {{ showForm ? 'Cancel' : '+ Add Account' }}
        </button>
      </div>
    </div>

    <form v-if="showForm" @submit.prevent="handleCreate" class="card-elevated p-5 space-y-3">
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="label-text">Account Name</label>
          <input v-model="form.name" placeholder="e.g. BPI Savings" required class="input-field" />
        </div>
        <div>
          <label class="label-text">Type</label>
          <select v-model="form.type" class="select-field">
            <option value="savings">Savings</option>
            <option value="checking">Checking</option>
            <option value="time_deposit">Time Deposit</option>
            <option value="investment">Investment</option>
          </select>
        </div>
        <div>
          <label class="label-text">Currency</label>
          <select v-model="form.currency" required class="select-field">
            <option value="PHP">PHP</option>
            <option value="USD">USD</option>
          </select>
        </div>
        <div>
          <label class="label-text">Initial Balance</label>
          <input v-model.number="form.initial_balance" type="number" step="0.01" class="input-field" />
        </div>
      </div>
      <button type="submit" class="btn-secondary text-xs">Create Account</button>
    </form>

    <div v-if="loading" class="text-center text-mushroom-400 py-8 text-sm">Loading...</div>

    <div v-else class="space-y-6">
      <div v-for="currency in currencyOrder" :key="currency" v-show="groupedAccounts[currency]">
        <div class="text-sm font-medium text-mushroom-700 mb-3">{{ currencyLabels[currency] || currency }}</div>

        <div class="space-y-3">
          <template v-for="acc in groupedAccounts[currency]" :key="acc.id">
            <div v-if="goalTypes.includes(acc.type)" class="card-elevated p-4 border-l-4" :class="accountTypeColors[acc.type] || 'border-l-mushroom-400'">
              <div class="flex items-center justify-between mb-3">
                <div>
                  <div class="text-sm font-medium text-mushroom-950">{{ acc.name }}</div>
                  <div class="text-xs text-mushroom-400">{{ accountTypeLabels[acc.type] }}</div>
                </div>
                <div class="text-right">
                  <div class="text-xl font-semibold text-mushroom-950">{{ formatCurrency(getBalance(acc.id), acc.currency) }}</div>
                </div>
              </div>

              <div v-if="acc.goal_amount > 0">
                <BudgetProgressBar
                  :spent="getBalance(acc.id)"
                  :budget="acc.goal_amount"
                  :greenThreshold="0.7"
                  :orangeThreshold="0.4"
                  class="mb-2"
                />
                <div class="flex items-center justify-between text-xs text-mushroom-500">
                  <span>
                    <template v-if="editingGoal === acc.id">
                      <input
                        v-model.number="goalValue"
                        @keyup.enter="saveGoal(acc)"
                        @keyup.escape="cancelGoal"
                        @blur="saveGoal(acc)"
                        type="number"
                        step="1"
                        min="0"
                        class="input-field text-xs py-0.5 px-1.5 w-24 inline"
                        autofocus
                      />
                    </template>
                    <template v-else>
                      <span @click="startEditGoal(acc)" class="cursor-pointer hover:text-kangkong-600">
                        {{ formatCurrency(acc.goal_amount, acc.currency) }}
                      </span>
                    </template>
                  </span>
                  <span>{{ goalProgress(getBalance(acc.id), acc.goal_amount).toFixed(1) }}%</span>
                </div>
              </div>

              <div v-else>
                <button @click="startEditGoal(acc)" class="text-xs text-kangkong-600 hover:text-kangkong-800">Set goal</button>
              </div>
            </div>

            <div v-else class="card p-3 border-l-4 flex items-center justify-between" :class="accountTypeColors[acc.type] || 'border-l-mushroom-400'">
              <div>
                <div class="text-sm font-medium text-mushroom-950">{{ acc.name }}</div>
                <div class="text-xs text-mushroom-400">{{ accountTypeLabels[acc.type] }}</div>
              </div>
              <div class="text-sm font-semibold text-mushroom-950">
                {{ formatCurrency(getBalance(acc.id), acc.currency) }}
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
