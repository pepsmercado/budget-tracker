<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useTransfers } from '../composables/useTransfers'
import { useAccounts } from '../composables/useAccounts'
import { useToast } from '../composables/useToast.js'
import Skeleton from '../components/Skeleton.vue'

const props = defineProps({ currency: { type: String, default: 'php' } })

const { transfers, loading, fetchTransfers, createTransfer, deleteTransfer } = useTransfers()
const { accounts, fetchAccounts } = useAccounts()
const toast = useToast()

const currencyParam = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')
const currencySymbol = computed(() => props.currency === 'usd' ? '$' : '₱')
const viewLabel = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')

const showForm = ref(false)
const confirmingDelete = ref(null)

const form = ref(emptyForm())

function emptyForm() {
  return { from_account_id: '', to_account_id: '', amount: 0, currency: currencyParam.value, fee: 0, date: new Date().toISOString().slice(0, 10), note: '' }
}

const currencyAccounts = computed(() => accounts.value.filter(a => a.currency === currencyParam.value))

function accountName(id) {
  const a = accounts.value.find(x => x.id === id)
  return a ? a.name : 'Unknown'
}

function formatDate(d) {
  if (!d) return '—'
  const dt = typeof d === 'string' ? new Date(d + 'T00:00:00') : new Date(d)
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function canSubmit() {
  return form.value.from_account_id && form.value.to_account_id &&
    form.value.from_account_id !== form.value.to_account_id &&
    form.value.amount > 0 && form.value.date
}

async function submitForm() {
  if (!canSubmit()) return
  try {
    await createTransfer(form.value)
    showForm.value = false
    form.value = emptyForm()
    await fetchTransfers(currencyParam.value)
    toast.success('Transfer created')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Transfer failed')
  }
}

async function handleDelete(t) {
  await deleteTransfer(t.id)
  confirmingDelete.value = null
  await fetchTransfers(currencyParam.value)
  toast.success('Transfer reversed')
}

async function loadAll() {
  await Promise.all([fetchTransfers(currencyParam.value), fetchAccounts()])
}

onMounted(loadAll)
watch(currencyParam, loadAll)
</script>

<template>
  <div class="space-y-5">

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-lg font-medium text-mushroom-950 dark:text-mushroom-50">{{ viewLabel }} Transfers</h2>
        <p class="text-xs text-mushroom-400 dark:text-mushroom-500 mt-0.5">Move money between accounts</p>
      </div>
      <button @click="showForm = !showForm" class="btn-primary text-xs">
        {{ showForm ? 'Cancel' : '+ New Transfer' }}
      </button>
    </div>

    <!-- Form -->
    <transition name="fade">
      <div v-if="showForm" class="card-elevated p-5 space-y-4">
        <h3 class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">New Transfer</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="label-text">From Account</label>
            <select v-model="form.from_account_id" class="select-field" required>
              <option value="" disabled>Select source...</option>
              <option v-for="a in currencyAccounts" :key="a.id" :value="a.id">{{ a.name }}</option>
            </select>
          </div>
          <div>
            <label class="label-text">To Account</label>
            <select v-model="form.to_account_id" class="select-field" required>
              <option value="" disabled>Select destination...</option>
              <option v-for="a in currencyAccounts" :key="a.id" :value="a.id" :disabled="a.id === form.from_account_id">{{ a.name }}</option>
            </select>
          </div>
          <div>
            <label class="label-text">Amount ({{ currencySymbol }})</label>
            <input v-model.number="form.amount" type="number" step="0.01" min="0.01" required class="input-field" />
          </div>
          <div>
            <label class="label-text">Fee ({{ currencySymbol }}) <span class="text-mushroom-300 dark:text-mushroom-600">optional</span></label>
            <input v-model.number="form.fee" type="number" step="0.01" min="0" class="input-field" />
          </div>
          <div>
            <label class="label-text">Date</label>
            <input v-model="form.date" type="date" required class="input-field" />
          </div>
          <div>
            <label class="label-text">Note <span class="text-mushroom-300 dark:text-mushroom-600">optional</span></label>
            <input v-model="form.note" placeholder="e.g. Monthly savings" class="input-field" />
          </div>
        </div>
        <button @click="submitForm" :disabled="!canSubmit()" class="btn-secondary text-xs disabled:opacity-40">Create Transfer</button>
      </div>
    </transition>

    <!-- Transfer list -->
    <div v-if="loading && !transfers.length" class="space-y-3">
      <div v-for="t in 3" :key="t" class="card-elevated p-4 border-l-4 border-l-mushroom-200 dark:border-l-mushroom-700">
        <div class="flex items-center justify-between">
          <div>
            <div class="flex items-center gap-2 mb-1">
              <Skeleton width="80px" height="14px" />
              <Skeleton width="14px" height="14px" />
              <Skeleton width="80px" height="14px" />
            </div>
            <div class="flex items-center gap-3">
              <Skeleton width="60px" height="10px" />
              <Skeleton width="50px" height="10px" />
            </div>
          </div>
          <div class="flex items-center gap-3">
            <Skeleton width="80px" height="18px" />
            <Skeleton width="20px" height="20px" />
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!transfers.length" class="text-center py-12">
      <div class="text-3xl mb-3">↔️</div>
      <p class="text-sm text-mushroom-500 dark:text-mushroom-400">No transfers yet</p>
      <p class="text-xs text-mushroom-400 dark:text-mushroom-500 mt-1">Click "New Transfer" to move money between accounts</p>
    </div>

    <div v-else class="space-y-3">
      <div v-for="t in transfers" :key="t.id" class="card-elevated p-4 border-l-4 border-l-blueberry-400">
        <div class="flex items-center justify-between">
          <div>
            <div class="flex items-center gap-2 mb-1">
              <span class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">{{ accountName(t.from_account_id) }}</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-mushroom-300 dark:text-mushroom-600"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              <span class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">{{ accountName(t.to_account_id) }}</span>
            </div>
            <div class="flex items-center gap-3 text-xs text-mushroom-400 dark:text-mushroom-500">
              <span>{{ formatDate(t.date) }}</span>
              <template v-if="t.fee > 0">
                <span class="text-mushroom-200 dark:text-mushroom-600">|</span>
                <span class="text-tomato-500 dark:text-tomato-400">Fee: {{ currencySymbol }}{{ t.fee.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}</span>
              </template>
              <template v-if="t.note">
                <span class="text-mushroom-200 dark:text-mushroom-600">|</span>
                <span>{{ t.note }}</span>
              </template>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-lg font-medium text-mushroom-950 dark:text-mushroom-50">{{ currencySymbol }}{{ t.amount.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}</span>
            <div class="flex items-center gap-1">
              <template v-if="confirmingDelete === t.id">
                <span class="text-xs text-mushroom-400 dark:text-mushroom-500 mr-1">Reverse?</span>
                <button @click="handleDelete(t)" class="text-tomato-500 hover:text-tomato-700 text-xs font-medium">Yes</button>
                <button @click="confirmingDelete = null" class="text-mushroom-400 dark:text-mushroom-500 hover:text-mushroom-600 dark:hover:text-mushroom-300 text-xs">No</button>
              </template>
              <button v-else @click="confirmingDelete = t.id" class="text-mushroom-300 dark:text-mushroom-600 hover:text-tomato-500 transition-colors" title="Reverse transfer">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
