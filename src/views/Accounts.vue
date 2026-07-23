<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAccounts } from '../composables/useAccounts'
import { useSummary } from '../composables/useSummary'

const { accounts, loading, fetchAccounts, createAccount, deleteAccount, updateAccount } = useAccounts()
const { balances, fetchBalances } = useSummary()

const showForm = ref(false)
const form = ref({ name: '', type: 'savings', currency: 'PHP', initial_balance: 0 })

const accountTypes = {
  savings: { label: 'Savings', icon: '🏦' },
  checking: { label: 'Checking', icon: '📋' },
  time_deposit: { label: 'Time Deposit', icon: '🔒' },
  investment: { label: 'Investment', icon: '📈' },
  credit_card: { label: 'Credit Card', icon: '💳' },
}

const groupedAccounts = computed(() => {
  const groups = {}
  for (const acc of accounts.value) {
    const type = acc.type
    if (!groups[type]) groups[type] = []
    groups[type].push(acc)
  }
  return groups
})

onMounted(async () => {
  await Promise.all([fetchAccounts(), fetchBalances()])
})

function getBalance(accountId) {
  const b = balances.value.find(x => x.account_id === accountId)
  return b ? b.balance : 0
}

async function handleCreate() {
  await createAccount(form.value)
  showForm.value = false
  form.value = { name: '', type: 'savings', currency: 'PHP', initial_balance: 0 }
  await fetchBalances()
}

async function handleDelete(id) {
  if (confirm('Delete this account?')) {
    await deleteAccount(id)
    await fetchBalances()
  }
}

const editingSub = ref(null)
const subForm = ref({ name: '', balance: 0 })

function startEditSub(account, sub) {
  editingSub.value = { accountId: account.id, subId: sub.id }
  subForm.value = { name: sub.name, balance: sub.balance }
}

async function saveSubAccount(account) {
  const updated = account.sub_accounts.map(s => {
    if (s.id === editingSub.value.subId) {
      return { ...s, name: subForm.value.name, balance: subForm.value.balance }
    }
    return s
  })
  await updateAccount(account.id, { ...account, sub_accounts: updated })
  editingSub.value = null
  await fetchBalances()
}

function cancelEditSub() {
  editingSub.value = null
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-medium text-mushroom-950">Accounts</h2>
      <button @click="showForm = !showForm" class="btn-primary text-xs">
        {{ showForm ? 'Cancel' : '+ Add Account' }}
      </button>
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
            <option value="credit_card">Credit Card</option>
          </select>
        </div>
        <div>
          <label class="label-text">Currency</label>
          <input v-model="form.currency" maxlength="3" placeholder="PHP" required class="input-field" />
        </div>
        <div>
          <label class="label-text">Initial Balance</label>
          <input v-model.number="form.initial_balance" type="number" step="0.01" class="input-field" />
        </div>
      </div>
      <button type="submit" class="btn-secondary text-xs">Create Account</button>
    </form>

    <div v-if="loading" class="text-center text-mushroom-400 py-8 text-sm">Loading...</div>

    <div v-else class="space-y-5">
      <div v-for="(accs, type) in groupedAccounts" :key="type">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-sm">{{ accountTypes[type]?.icon || '💰' }}</span>
          <h3 class="text-sm font-medium text-mushroom-700">{{ accountTypes[type]?.label || type }}</h3>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div v-for="a in accs" :key="a.id" class="card p-4">
            <div class="flex items-center justify-between mb-1">
              <div class="text-sm font-medium text-mushroom-950">{{ a.name }}</div>
              <div class="text-sm font-semibold text-mushroom-950">
                {{ a.currency }} {{ getBalance(a.id).toLocaleString(undefined, { minimumFractionDigits: 2 }) }}
              </div>
            </div>
            <div class="text-xs text-mushroom-400">{{ a.currency }}</div>

            <div v-if="a.sub_accounts && a.sub_accounts.length > 0" class="mt-3 pt-3 border-t border-mushroom-100">
              <div class="text-xs font-medium text-mushroom-400 mb-1.5">Sub-Accounts</div>
              <div v-for="sub in a.sub_accounts" :key="sub.id" class="flex items-center justify-between py-1 text-xs">
                <template v-if="editingSub && editingSub.accountId === a.id && editingSub.subId === sub.id">
                  <input v-model="subForm.name" class="input-field w-20 text-xs py-1" />
                  <input v-model.number="subForm.balance" type="number" step="0.01" class="input-field w-20 text-xs py-1" />
                  <button @click="saveSubAccount(a)" class="text-kangkong-600 font-medium">Save</button>
                  <button @click="cancelEditSub" class="text-mushroom-400">Cancel</button>
                </template>
                <template v-else>
                  <span class="text-mushroom-500">{{ sub.name }}</span>
                  <div class="flex items-center gap-2">
                    <span class="font-medium text-mushroom-700">{{ a.currency }} {{ sub.balance.toLocaleString() }}</span>
                    <button @click="startEditSub(a, sub)" class="text-tomato-500 font-medium">Edit</button>
                  </div>
                </template>
              </div>
            </div>

            <div class="mt-2 flex justify-end">
              <button @click="handleDelete(a.id)" class="text-xs text-mushroom-400 hover:text-tomato-600">Delete</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
