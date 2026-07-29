<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRecurring } from '../composables/useRecurring'
import { useAccounts } from '../composables/useAccounts'
import { useToast } from '../composables/useToast.js'
import Skeleton from '../components/Skeleton.vue'
import { formatDate, formatCurrency } from '../utils/format.js'
import { currencySymbol } from '../utils/currency.js'
import { categoryIcons } from '../constants.js'

const props = defineProps({ currency: { type: String, default: 'php' } })

const { rules, loading, fetchRules, createRule, updateRule, deleteRule, toggleRule, runNow } = useRecurring()
const { accounts, fetchAccounts } = useAccounts()
const toast = useToast()

const currencyParam = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')
const curSym = computed(() => currencySymbol(currencyParam.value))
const viewLabel = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')

const showForm = ref(false)
const editingRule = ref(null)
const confirmingDelete = ref(null)

const form = ref(emptyForm())

function emptyForm() {
  return { name: '', account_id: '', category: 'Rent', amount: 0, currency: currencyParam.value, frequency: 'monthly', day_of_month: 1, start_date: '', end_date: '' }
}

const categoryOptions = Object.keys(categoryIcons)

const frequencyLabels = { monthly: 'Monthly', yearly: 'Yearly' }

const currencyAccounts = computed(() => accounts.value.filter(a => a.currency === currencyParam.value))



function nextDateLabel(r) {
  if (!r.next_date) return 'Not scheduled'
  const today = new Date().toISOString().slice(0, 10)
  if (r.next_date <= today) return 'Due now'
  return 'Next: ' + formatDate(r.next_date)
}

function nextDateClass(r) {
  if (!r.next_date) return 'text-mushroom-400 dark:text-mushroom-500'
  const today = new Date().toISOString().slice(0, 10)
  if (r.next_date <= today) return 'text-tomato-600 font-medium'
  return 'text-mushroom-400 dark:text-mushroom-500'
}

function startCreate() {
  editingRule.value = null
  form.value = emptyForm()
  showForm.value = true
}

function startEdit(r) {
  editingRule.value = r.id
  form.value = {
    name: r.name,
    account_id: r.account_id,
    category: r.category,
    amount: r.amount,
    currency: r.currency,
    frequency: r.frequency,
    day_of_month: r.day_of_month,
    start_date: r.start_date,
    end_date: r.end_date || '',
  }
  showForm.value = true
}

function cancelForm() {
  showForm.value = false
  editingRule.value = null
  form.value = emptyForm()
}

async function submitForm() {
  try {
    if (editingRule.value) {
      await updateRule(editingRule.value, form.value)
    } else {
      await createRule(form.value)
    }
    showForm.value = false
    editingRule.value = null
    form.value = emptyForm()
    await fetchRules(currencyParam.value)
  } catch (e) {
    console.error('Failed to save rule:', e)
    toast.error('Failed to save rule: ' + (e.response?.data?.detail || e.message))
  }
}

async function handleDelete(r) {
  try {
    await deleteRule(r.id)
    confirmingDelete.value = null
  } catch (e) {
    console.error('Failed to delete rule:', e)
    toast.error('Failed to delete rule: ' + (e.response?.data?.detail || e.message))
  }
}

async function handleToggle(r) {
  try {
    await toggleRule(r.id, !r.active)
  } catch (e) {
    console.error('Failed to toggle rule:', e)
    toast.error('Failed to toggle rule: ' + (e.response?.data?.detail || e.message))
  }
}

async function handleRun() {
  try {
    const result = await runNow(currencyParam.value)
    const msg = result.generated === 0 ? 'No transactions generated' : `Generated ${result.generated} transaction${result.generated > 1 ? 's' : ''}`
    toast.success(msg)
    await fetchRules(currencyParam.value)
  } catch (e) {
    console.error('Failed to run rules:', e)
    toast.error('Failed to run rules: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadAll() {
  await Promise.all([fetchRules(currencyParam.value), fetchAccounts()])
}

onMounted(loadAll)
watch(currencyParam, loadAll)
</script>

<template>
  <div class="space-y-5">

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-lg font-medium text-mushroom-950 dark:text-mushroom-50">{{ viewLabel }} Recurring</h2>
        <p class="text-xs text-mushroom-400 dark:text-mushroom-500 mt-0.5">Automated expense templates</p>
      </div>
      <div class="flex items-center gap-3">
        <button @click="handleRun" class="btn-primary text-xs flex items-center gap-1.5">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/><polyline points="21 3 21 9 15 9"/></svg>
          Run Now
        </button>
        <button @click="startCreate" class="btn-secondary text-xs">+ Add Rule</button>
      </div>
    </div>

    <!-- Form -->
    <transition name="fade">
      <div v-if="showForm" class="card-elevated p-5 space-y-4">
        <h3 class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">{{ editingRule ? 'Edit Rule' : 'New Recurring Rule' }}</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="label-text">Name</label>
            <input v-model="form.name" placeholder="e.g. Rent" required class="input-field" />
          </div>
          <div>
            <label class="label-text">Amount ({{ curSym }})</label>
            <input v-model.number="form.amount" type="number" step="0.01" min="0" required class="input-field" />
          </div>
          <div>
            <label class="label-text">Account</label>
            <select v-model="form.account_id" class="select-field" required>
              <option value="" disabled>Select account...</option>
              <option v-for="a in currencyAccounts" :key="a.id" :value="a.id">{{ a.name }}</option>
            </select>
          </div>
          <div>
            <label class="label-text">Category</label>
            <select v-model="form.category" class="select-field">
              <option v-for="c in categoryOptions" :key="c" :value="c">{{ categoryIcons[c] }} {{ c }}</option>
            </select>
          </div>
          <div>
            <label class="label-text">Frequency</label>
            <select v-model="form.frequency" class="select-field">
              <option value="monthly">Monthly</option>
              <option value="yearly">Yearly</option>
            </select>
          </div>
          <div>
            <label class="label-text">Day of Month</label>
            <input v-model.number="form.day_of_month" type="number" min="1" max="28" required class="input-field" />
          </div>
          <div>
            <label class="label-text">Start Date</label>
            <input v-model="form.start_date" type="date" required class="input-field" />
          </div>
          <div>
            <label class="label-text">End Date <span class="text-mushroom-300 dark:text-mushroom-600">(optional)</span></label>
            <input v-model="form.end_date" type="date" class="input-field" />
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button @click="submitForm" class="btn-primary text-xs">{{ editingRule ? 'Save Changes' : 'Create Rule' }}</button>
          <button @click="cancelForm" class="text-xs text-mushroom-400 dark:text-mushroom-500 hover:text-mushroom-600 dark:hover:text-mushroom-300">Cancel</button>
        </div>
      </div>
    </transition>

    <!-- Rules list -->
    <div v-if="loading && !rules.length" class="space-y-3">
      <div v-for="r in 3" :key="r" class="card-elevated p-4 border-l-4 border-l-mushroom-200 dark:border-l-mushroom-700">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <Skeleton width="36px" height="20px" rounded="rounded-full" />
            <div class="space-y-1.5">
              <div class="flex items-center gap-2">
                <Skeleton width="20px" height="20px" />
                <Skeleton width="100px" height="14px" />
                <Skeleton width="50px" height="14px" rounded="rounded-full" />
              </div>
              <div class="flex items-center gap-3">
                <Skeleton width="80px" height="10px" />
                <Skeleton width="60px" height="10px" />
                <Skeleton width="70px" height="10px" />
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Skeleton width="20px" height="20px" />
            <Skeleton width="20px" height="20px" />
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!rules.length" class="text-center py-12">
      <div class="text-3xl mb-3">🔄</div>
      <p class="text-sm text-mushroom-500 dark:text-mushroom-400">No recurring rules yet</p>
      <p class="text-xs text-mushroom-400 dark:text-mushroom-500 mt-1">Click "Add Rule" to set up automated expenses</p>
    </div>

    <div v-else class="space-y-3">
      <div v-for="r in rules" :key="r.id" class="card-elevated p-4 border-l-4" :class="r.active ? 'border-l-kangkong-500' : 'border-l-mushroom-200 dark:border-l-mushroom-700'">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <button
              @click="handleToggle(r)"
              class="relative w-9 h-5 rounded-full transition-colors"
              :class="r.active ? 'bg-kangkong-500' : 'bg-mushroom-200 dark:bg-mushroom-700'"
              :title="r.active ? 'Disable' : 'Enable'"
            >
              <span class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform" :class="r.active ? 'translate-x-4' : ''" />
            </button>
            <div>
              <div class="flex items-center gap-2">
                <span class="text-lg">{{ categoryIcons[r.category] || '📋' }}</span>
                <span class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">{{ r.name }}</span>
                <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium" :class="r.active ? 'bg-kangkong-100 text-kangkong-700 dark:bg-kangkong-500/15 dark:text-kangkong-400' : 'bg-mushroom-100 text-mushroom-400 dark:bg-mushroom-700 dark:text-mushroom-500'">{{ r.active ? 'Active' : 'Paused' }}</span>
              </div>
              <div class="flex items-center gap-3 mt-1 text-xs text-mushroom-400 dark:text-mushroom-500">
                <span>{{ frequencyLabels[r.frequency] }} on {{ r.day_of_month }}{{ r.day_of_month === 1 ? 'st' : r.day_of_month === 2 ? 'nd' : r.day_of_month === 3 ? 'rd' : 'th' }}</span>
                <span class="text-mushroom-200 dark:text-mushroom-600">|</span>
                <span class="font-medium text-mushroom-700 dark:text-mushroom-300">{{ formatCurrency(r.amount, curSym) }}</span>
                <span class="text-mushroom-200 dark:text-mushroom-600">|</span>
                <span :class="nextDateClass(r)">{{ nextDateLabel(r) }}</span>
                <template v-if="r.end_date">
                  <span class="text-mushroom-200 dark:text-mushroom-600">|</span>
                  <span>Ends {{ formatDate(r.end_date) }}</span>
                </template>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button @click="startEdit(r)" class="text-mushroom-300 dark:text-mushroom-600 hover:text-blueberry-500 dark:hover:text-blueberry-400 transition-colors" title="Edit">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
            <template v-if="confirmingDelete === r.id">
              <span class="text-xs text-mushroom-400 dark:text-mushroom-500 mr-1">Delete?</span>
              <button @click="handleDelete(r)" class="text-tomato-500 hover:text-tomato-700 text-xs font-medium">Yes</button>
              <button @click="confirmingDelete = null" class="text-mushroom-400 dark:text-mushroom-500 hover:text-mushroom-600 dark:hover:text-mushroom-300 text-xs">No</button>
            </template>
            <button v-else @click="confirmingDelete = r.id" class="text-mushroom-300 dark:text-mushroom-600 hover:text-tomato-500 dark:hover:text-tomato-400 transition-colors" title="Delete">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
            </button>
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
