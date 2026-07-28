<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useAccounts } from '../composables/useAccounts'
import { useSummary } from '../composables/useSummary'
import BudgetProgressBar from '../components/BudgetProgressBar.vue'
import Skeleton from '../components/Skeleton.vue'
import { useToast } from '../composables/useToast.js'

const props = defineProps({ currency: { type: String, default: 'php' } })

const { accounts, loading, fetchAccounts, createAccount, deleteAccount, updateAccount, updateAccountGoal } = useAccounts()
const { balances, fetchBalances } = useSummary()
const toast = useToast()

const currencyParam = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')
const currencySymbol = computed(() => props.currency === 'usd' ? '$' : '₱')
const viewLabel = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')

const showForm = ref(false)
const form = ref({ name: '', type: 'savings', currency: currencyParam.value, bank: '', account_number: '', initial_balance: 0 })
const customBank = ref('')
const creating = ref(false)
const eyeHidden = ref(false)
const editingGoal = ref(null)
const goalValue = ref(0)
const editingMaturity = ref(null)
const maturityValue = ref('')
const editingName = ref(null)
const nameValue = ref('')
const confirmingDelete = ref(null)
const editingAcctNum = ref(null)
const acctNumValue = ref('')
const confirmingAcctNum = ref(null)

const bankColors = {
  BPI: 'bg-tomato-100 text-tomato-700 dark:bg-tomato-500/15 dark:text-tomato-400',
  BDO: 'bg-blueberry-100 text-blueberry-700 dark:bg-blueberry-500/15 dark:text-blueberry-400',
  Maya: 'bg-kangkong-100 text-kangkong-700 dark:bg-kangkong-500/15 dark:text-kangkong-400',
  'Bank of America': 'bg-blueberry-100 text-blueberry-700 dark:bg-blueberry-500/15 dark:text-blueberry-400',
}

const bankOptions = [
  'BPI', 'BDO', 'Maya', 'Security Bank', 'Metrobank', 'Landbank', 'PNB', 'EastWest',
  'Bank of America', 'Chase', 'Wells Fargo', 'Citi', 'US Bank', 'Other',
]

const accountTypeLabels = {
  savings: 'Savings',
  checking: 'Checking',
  time_deposit: 'Time Deposit',
  equity: 'Equity',
  investment: 'Investment',
  credit_card: 'Credit Card',
}

const accountTypeColors = {
  savings: 'border-l-kangkong-500',
  checking: 'border-l-blueberry-500',
  time_deposit: 'border-l-mango-500',
  equity: 'border-l-purple-500',
  investment: 'border-l-purple-500',
}

const groupedByType = computed(() => {
  const typeOrder = ['savings', 'time_deposit', 'equity', 'checking', 'investment']
  const groups = {}
  for (const acc of accounts.value) {
    if (acc.currency !== currencyParam.value) continue
    if (!groups[acc.type]) groups[acc.type] = []
    groups[acc.type].push(acc)
  }
  const ordered = []
  for (const type of typeOrder) {
    if (groups[type]) {
      ordered.push({ type, label: accountTypeLabels[type] || type, accounts: groups[type] })
    }
  }
  return ordered
})

function getBalance(accountId) {
  const b = balances.value.find(x => x.account_id === accountId)
  return b ? b.balance : 0
}

function formatCurrency(val) {
  if (eyeHidden.value) return '***'
  return `${currencySymbol.value}${val.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
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

function startEditMaturity(acc) {
  editingMaturity.value = acc.id
  maturityValue.value = acc.maturity_date || ''
}

async function saveMaturity(acc) {
  await updateAccount(acc.id, {
    name: acc.name,
    type: acc.type,
    currency: acc.currency,
    bank: acc.bank || '',
    account_number: acc.account_number || '',
    initial_balance: acc.initial_balance,
    goal_amount: acc.goal_amount || 0,
    sub_accounts: acc.sub_accounts || [],
    dividend_type: acc.dividend_type || '',
    maturity_date: maturityValue.value,
  })
  editingMaturity.value = null
}

function cancelMaturity() {
  editingMaturity.value = null
}

function startEditName(acc) {
  editingName.value = acc.id
  nameValue.value = acc.name
}

async function saveName(acc) {
  if (nameValue.value.trim() && nameValue.value.trim() !== acc.name) {
    editingName.value = null
    await updateAccount(acc.id, {
      name: nameValue.value.trim(),
      type: acc.type,
      currency: acc.currency,
      bank: acc.bank || '',
      account_number: acc.account_number || '',
      initial_balance: acc.initial_balance,
      goal_amount: acc.goal_amount || 0,
      sub_accounts: acc.sub_accounts || [],
      dividend_type: acc.dividend_type || '',
      maturity_date: acc.maturity_date || '',
    })
  } else {
    editingName.value = null
  }
}

function cancelName() {
  editingName.value = null
}

function startEditAcctNum(acc) {
  editingAcctNum.value = acc.id
  acctNumValue.value = acc.account_number || ''
}

function confirmSaveAcctNum(acc) {
  confirmingAcctNum.value = acc.id
}

async function saveAcctNum(acc) {
  await updateAccount(acc.id, {
    name: acc.name,
    type: acc.type,
    currency: acc.currency,
    bank: acc.bank || '',
    account_number: acctNumValue.value.trim(),
    initial_balance: acc.initial_balance,
    goal_amount: acc.goal_amount || 0,
    sub_accounts: acc.sub_accounts || [],
    dividend_type: acc.dividend_type || '',
    maturity_date: acc.maturity_date || '',
  })
  confirmingAcctNum.value = null
  editingAcctNum.value = null
}

function cancelAcctNum() {
  confirmingAcctNum.value = null
  editingAcctNum.value = null
}

async function handleDelete(acc) {
  try {
    await deleteAccount(acc.id)
    confirmingDelete.value = null
    await fetchBalances(currencyParam.value)
  } catch (e) {
    console.error('Failed to delete account:', e)
  }
}

async function loadAll() {
  await Promise.all([fetchAccounts(), fetchBalances(currencyParam.value)])
}

onMounted(loadAll)

watch(currencyParam, () => {
  loadAll()
})

async function handleCreate() {
  creating.value = true
  try {
    const payload = { ...form.value }
    if (payload.bank === 'Other' && customBank.value.trim()) {
      payload.bank = customBank.value.trim()
    }
    await createAccount(payload)
    showForm.value = false
    customBank.value = ''
    form.value = { name: '', type: 'savings', currency: currencyParam.value, bank: '', account_number: '', initial_balance: 0 }
    await fetchBalances(currencyParam.value)
  } catch (e) {
    console.error('Create account failed:', e)
    toast.error(e.response?.data?.detail || 'Failed to create account')
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-medium text-mushroom-950 dark:text-mushroom-50">{{ viewLabel }} Accounts</h2>
      <div class="flex items-center gap-3">
        <button @click="eyeHidden = !eyeHidden" class="text-mushroom-400 dark:text-mushroom-500 hover:text-mushroom-600 dark:hover:text-mushroom-300">
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
          <input v-model="form.name" placeholder="e.g. Savings" required class="input-field" />
        </div>
        <div>
          <label class="label-text">Bank</label>
          <select v-model="form.bank" class="select-field">
            <option value="">Select bank...</option>
            <option v-for="b in bankOptions" :key="b" :value="b">{{ b }}</option>
          </select>
          <input v-if="form.bank === 'Other'" v-model="customBank" placeholder="Enter bank name..." class="input-field mt-1.5 text-xs" />
        </div>
        <div>
          <label class="label-text">Type</label>
          <select v-model="form.type" class="select-field">
            <option value="savings">Savings</option>
            <option value="checking">Checking</option>
            <option value="time_deposit">Time Deposit</option>
            <option value="equity">Equity</option>
            <option value="investment">Investment</option>
          </select>
        </div>
        <div>
          <label class="label-text">Account Number</label>
          <input v-model="form.account_number" placeholder="e.g. ****4521" class="input-field" />
        </div>
        <div>
          <label class="label-text">Initial Balance</label>
          <input v-model.number="form.initial_balance" type="number" step="0.01" class="input-field" />
        </div>
      </div>
      <button type="submit" :disabled="creating" class="btn-secondary text-xs">
        {{ creating ? 'Creating...' : 'Create Account' }}
      </button>
    </form>

    <!-- Skeleton loading -->
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
            <div class="mt-3 pt-3 border-t border-mushroom-100 dark:border-mushroom-700/50 space-y-2">
              <Skeleton width="60px" height="10px" />
              <Skeleton width="100%" height="8px" rounded="rounded" />
              <div class="flex justify-between">
                <Skeleton width="50px" height="10px" />
                <Skeleton width="40px" height="10px" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="space-y-6">
      <div v-for="(group, gi) in groupedByType" :key="group.type">
        <h3 class="text-xs font-semibold uppercase tracking-wider text-mushroom-400 dark:text-mushroom-500 mb-3 mt-4 first:mt-0">{{ group.label }}</h3>

        <div class="space-y-3">
          <div v-for="acc in group.accounts" :key="acc.id" class="card-elevated p-4 border-l-4" :class="accountTypeColors[acc.type] || 'border-l-mushroom-400'">
            <div class="flex items-center justify-between mb-2">
              <div>
                <div class="flex items-center gap-2.5 mb-1">
                  <span v-if="acc.bank" class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium" :class="bankColors[acc.bank] || 'bg-mushroom-100 dark:bg-mushroom-800 text-mushroom-600 dark:text-mushroom-400'">{{ acc.bank }}</span>
                  <input
                    v-show="editingName === acc.id"
                    v-model="nameValue"
                    @keyup.enter="saveName(acc)"
                    @keyup.escape="cancelName"
                    class="input-field text-sm font-medium py-0.5 px-1.5 w-48"
                    :ref="el => { if (el && editingName === acc.id) el.focus() }"
                  />
                  <span
                    v-show="editingName !== acc.id"
                    class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50 cursor-pointer hover:text-kangkong-600 dark:hover:text-kangkong-400"
                    @click="startEditName(acc)"
                  >{{ acc.name }}</span>
                </div>
                <template v-if="editingAcctNum === acc.id">
                  <template v-if="confirmingAcctNum === acc.id">
                    <div class="flex items-center gap-1.5 mt-1">
                      <span class="text-xs text-mushroom-400 dark:text-mushroom-500">Save change?</span>
                      <button @click="saveAcctNum(acc)" class="text-kangkong-600 hover:text-kangkong-800 text-xs font-medium">Yes</button>
                      <button @click="cancelAcctNum" class="text-mushroom-400 dark:text-mushroom-500 hover:text-mushroom-600 dark:hover:text-mushroom-300 text-xs">No</button>
                    </div>
                  </template>
                  <template v-else>
                    <div class="flex items-center gap-1 mt-1">
                      <input
                        v-model="acctNumValue"
                        @keyup.enter="confirmSaveAcctNum(acc)"
                        @keyup.escape="cancelAcctNum"
                        class="input-field text-xs py-0.5 px-1.5 w-28"
                        placeholder="e.g. ****4521"
                        autofocus
                      />
                    </div>
                  </template>
                </template>
                <div v-else-if="acc.account_number" class="text-xs text-mushroom-400 dark:text-mushroom-500 mt-1 cursor-pointer hover:text-kangkong-600 dark:hover:text-kangkong-400" @click="startEditAcctNum(acc)">{{ acc.account_number }}</div>
                <div v-else class="text-xs text-mushroom-300 dark:text-mushroom-600 mt-1 cursor-pointer hover:text-kangkong-600 dark:hover:text-kangkong-400" @click="startEditAcctNum(acc)">+ Add account number</div>
                <div v-if="acc.dividend_type" class="text-xs text-mushroom-400 dark:text-mushroom-500 mt-1">{{ acc.dividend_type }}</div>
                <template v-if="acc.type === 'time_deposit'">
                  <template v-if="editingMaturity === acc.id">
                    <div class="flex items-center gap-2 mt-2 pt-2 border-t border-mushroom-100 dark:border-mushroom-700/50">
                      <input
                        v-model="maturityValue"
                        @keyup.enter="saveMaturity(acc)"
                        @keyup.escape="cancelMaturity"
                        type="date"
                        class="input-field text-xs py-0.5 px-1.5 w-36"
                        autofocus
                      />
                    </div>
                  </template>
                  <template v-else>
                    <div class="text-xs text-mushroom-400 dark:text-mushroom-500 cursor-pointer hover:text-kangkong-600 dark:hover:text-kangkong-400 mt-2 pt-2 border-t border-mushroom-100 dark:border-mushroom-700/50" @click="startEditMaturity(acc)">
                      {{ acc.maturity_date ? 'Maturity: ' + acc.maturity_date : '+ Set maturity date' }}
                    </div>
                  </template>
                </template>
                <div v-else-if="acc.maturity_date" class="text-xs text-mushroom-400 dark:text-mushroom-500 mt-2 pt-2 border-t border-mushroom-100 dark:border-mushroom-700/50">Maturity: {{ acc.maturity_date }}</div>
              </div>
              <div class="text-right">
                <div class="text-xl font-semibold text-mushroom-950 dark:text-mushroom-50">{{ formatCurrency(getBalance(acc.id)) }}</div>
                <div class="flex justify-end mt-1">
                  <template v-if="confirmingDelete === acc.id">
                    <span class="text-xs text-mushroom-400 dark:text-mushroom-500 mr-1">Delete?</span>
                    <button @click="handleDelete(acc)" class="text-tomato-500 hover:text-tomato-700 text-xs font-medium mr-1">Yes</button>
                    <button @click="confirmingDelete = null" class="text-mushroom-400 dark:text-mushroom-500 hover:text-mushroom-600 dark:hover:text-mushroom-300 text-xs">No</button>
                  </template>
                  <button v-else @click="confirmingDelete = acc.id" class="text-mushroom-300 dark:text-mushroom-600 hover:text-tomato-500 dark:hover:text-tomato-400 transition-colors" title="Delete account">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                  </button>
                </div>
              </div>
            </div>

            <template v-if="acc.type === 'savings' && !(acc.bank === 'BPI' && acc.name === 'Settlement')">
              <div class="mt-3 pt-3 border-t border-mushroom-100 dark:border-mushroom-700/50">
                <template v-if="editingGoal === acc.id">
                  <div class="flex items-center gap-2">
                    <input
                      v-model.number="goalValue"
                      @keyup.enter="saveGoal(acc)"
                      @keyup.escape="cancelGoal"
                      @blur="saveGoal(acc)"
                      type="number"
                      step="1"
                      min="0"
                      class="input-field text-xs py-0.5 px-1.5 w-24"
                      autofocus
                    />
                    <span class="text-xs text-mushroom-400 dark:text-mushroom-500">Press Enter to save</span>
                  </div>
                </template>
                <template v-else>
                  <BudgetProgressBar
                    v-if="acc.goal_amount > 0"
                    :spent="getBalance(acc.id)"
                    :budget="acc.goal_amount"
                    :invert="true"
                    class="mb-2"
                  />
                  <div v-if="acc.goal_amount > 0" class="flex items-center justify-between text-xs text-mushroom-500 dark:text-mushroom-400">
                    <span @click="startEditGoal(acc)" class="cursor-pointer hover:text-kangkong-600 dark:hover:text-kangkong-400">
                      Goal: {{ formatCurrency(acc.goal_amount) }}
                    </span>
                    <span>{{ goalProgress(getBalance(acc.id), acc.goal_amount).toFixed(1) }}%</span>
                  </div>
                  <button v-else @click="startEditGoal(acc)" class="text-xs text-kangkong-600 hover:text-kangkong-800">Set goal</button>
                </template>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
