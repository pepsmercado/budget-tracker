<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../api'
import { useToast } from '../composables/useToast.js'
import Skeleton from '../components/Skeleton.vue'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const currencyParam = computed(() => route.path.startsWith('/usd') ? 'USD' : 'PHP')
const currency = computed(() => route.path.startsWith('/usd') ? 'usd' : 'php')

const activeTab = ref('bank')

const bankFile = ref(null)
const bank = ref('auto')
const bankAccountId = ref('')
const bankPreview = ref(null)
const bankLoading = ref(false)
const bankError = ref('')

const bulkFile = ref(null)
const bulkPreview = ref(null)
const bulkLoading = ref(false)
const bulkError = ref('')

const accounts = ref([])
const categories = ref([])
const loading = ref(false)

const expenseCategories = computed(() => categories.value.filter(c => c.type === 'expense'))
const groupedAccounts = computed(() => {
  const filtered = accounts.value.filter(a => a.currency === currencyParam.value)
  const groups = {}
  for (const a of filtered) {
    if (!groups[a.type]) groups[a.type] = []
    groups[a.type].push(a)
  }
  return groups
})

const flaggedCount = computed(() => {
  if (!bulkPreview.value?.rows) return 0
  return bulkPreview.value.rows.filter(r => r.warnings?.length > 0).length
})

async function loadAccounts() {
  loading.value = true
  try {
    const [accRes, catRes] = await Promise.all([api.get('/accounts'), api.get('/categories')])
    accounts.value = accRes.data
    categories.value = catRes.data
  } finally {
    loading.value = false
  }
}

onMounted(loadAccounts)

watch(currencyParam, loadAccounts)

const bankOptions = [
  { value: 'auto', label: 'Auto-detect' },
  { value: 'bpi', label: 'BPI' },
  { value: 'bdo', label: 'BDO' },
  { value: 'maya', label: 'Maya' },
  { value: 'bank_of_america', label: 'Bank of America' },
]

function handleBankFileChange(e) {
  bankFile.value = e.target.files[0]
  bankPreview.value = null
  bankError.value = ''
}

async function handleBankPreview() {
  if (!bankFile.value) return
  bankLoading.value = true
  bankError.value = ''
  try {
    const formData = new FormData()
    formData.append('file', bankFile.value)
    formData.append('bank', bank.value)
    const { data } = await api.post('/upload/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    bankPreview.value = data
  } catch (e) {
    bankError.value = e.response?.data?.detail || 'Failed to parse CSV'
  } finally {
    bankLoading.value = false
  }
}

function resetBank() {
  bankFile.value = null
  bankPreview.value = null
  bankError.value = ''
}

async function handleBankImport() {
  if (!bankPreview.value?.rows?.length || !bankAccountId.value) return
  bankLoading.value = true
  bankError.value = ''
  try {
    const { data } = await api.post('/upload/bank-import', {
      rows: bankPreview.value.rows,
      account_id: bankAccountId.value,
    })
    if (data.errors.length) {
      bankError.value = data.errors.join('\n')
    } else {
      toast.success(`Imported ${data.created} transactions`)
      resetBank()
      router.push(`/${currency.value}/transactions`)
    }
  } catch (e) {
    bankError.value = e.response?.data?.detail || 'Failed to import'
    toast.error(e.response?.data?.detail || 'Failed to import')
  } finally {
    bankLoading.value = false
  }
}

function handleBulkFileChange(e) {
  bulkFile.value = e.target.files[0]
  bulkPreview.value = null
  bulkError.value = ''
}

async function handleBulkPreview() {
  if (!bulkFile.value) return
  bulkLoading.value = true
  bulkError.value = ''
  try {
    const formData = new FormData()
    formData.append('file', bulkFile.value)
    const { data } = await api.post('/upload/bulk-preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    bulkPreview.value = data
  } catch (e) {
    bulkError.value = e.response?.data?.detail || 'Failed to parse CSV'
  } finally {
    bulkLoading.value = false
  }
}

function resetBulk() {
  bulkFile.value = null
  bulkPreview.value = null
  bulkError.value = ''
}

function removeRow(i) {
  bulkPreview.value.rows.splice(i, 1)
  bulkPreview.value.total_rows = bulkPreview.value.rows.length
  bulkPreview.value.total_income = bulkPreview.value.rows.filter(r => r.type === 'income').reduce((s, r) => s + r.amount, 0)
  bulkPreview.value.total_expense = bulkPreview.value.rows.filter(r => r.type === 'expense').reduce((s, r) => s + r.amount, 0)
}

async function handleBulkImport() {
  if (!bulkPreview.value?.rows?.length) return
  bulkLoading.value = true
  bulkError.value = ''
  try {
    const { data } = await api.post('/upload/bulk-import', { rows: bulkPreview.value.rows })
    if (data.errors.length) {
      bulkError.value = data.errors.join('\n')
    } else {
      toast.success(`Imported ${data.created} transactions`)
      resetBulk()
      router.push(`/${currency.value}/transactions`)
    }
  } catch (e) {
    bulkError.value = e.response?.data?.detail || 'Failed to import'
    toast.error(e.response?.data?.detail || 'Failed to import')
  } finally {
    bulkLoading.value = false
  }
}

function downloadTemplate() {
  window.open('/api/upload/template', '_blank')
}

function downloadLegend() {
  window.open('/api/upload/legend', '_blank')
}

function getWarningFor(row, field) {
  if (!row.warnings) return null
  return row.warnings.find(w => w.includes(field)) || null
}

function getSuggestion(warning) {
  if (!warning) return null
  const arrowMatch = warning.match(/→\s*'(.+?)'/)
  return arrowMatch ? arrowMatch[1] : null
}

function acceptSuggestion(row, field, warning) {
  const suggestion = getSuggestion(warning)
  if (!suggestion) return
  if (field === 'Account') row.account_id = suggestion
  else if (field === 'Category') row.category = suggestion
  else if (field === 'Sub-account') row.sub_account_id = suggestion
  row.warnings = row.warnings.filter(w => w !== warning)
}

function dismissWarning(row, warning) {
  row.warnings = row.warnings.filter(w => w !== warning)
}

function acceptAllSuggestions(rows) {
  for (const row of rows) {
    if (!row.warnings?.length) continue
    for (const warning of [...row.warnings]) {
      const suggestion = getSuggestion(warning)
      if (suggestion) {
        if (warning.includes('Account')) row.account_id = suggestion
        else if (warning.includes('Category')) row.category = suggestion
        else if (warning.includes('Sub-account')) row.sub_account_id = suggestion
      }
      row.warnings = row.warnings.filter(w => w !== warning)
    }
  }
}
</script>

<template>
  <div class="space-y-5">
    <h2 class="text-lg font-medium text-mushroom-950 dark:text-mushroom-50">Bulk Upload</h2>

    <div class="flex gap-1 bg-mushroom-100 dark:bg-mushroom-800 rounded-lg p-1 w-fit">
      <button
        @click="activeTab = 'bank'"
        class="px-4 py-1.5 text-xs font-medium rounded-md transition-colors"
        :class="activeTab === 'bank' ? 'bg-white dark:bg-mushroom-900 text-mushroom-900 dark:text-mushroom-50 shadow-sm' : 'text-mushroom-500 dark:text-mushroom-400 hover:text-mushroom-700 dark:hover:text-mushroom-200'"
      >
        Bank Statement
      </button>
      <button
        @click="activeTab = 'bulk'"
        class="px-4 py-1.5 text-xs font-medium rounded-md transition-colors"
        :class="activeTab === 'bulk' ? 'bg-white dark:bg-mushroom-900 text-mushroom-900 dark:text-mushroom-50 shadow-sm' : 'text-mushroom-500 dark:text-mushroom-400 hover:text-mushroom-700 dark:hover:text-mushroom-200'"
      >
        CSV Template
      </button>
    </div>

    <!-- Skeleton loading -->
    <div v-if="loading" class="space-y-4">
      <div class="card-elevated p-5 space-y-3">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <Skeleton width="60px" height="14px" class="mb-1" />
            <Skeleton width="100%" height="36px" rounded="rounded" />
          </div>
          <div>
            <Skeleton width="60px" height="14px" class="mb-1" />
            <Skeleton width="100%" height="36px" rounded="rounded" />
          </div>
        </div>
        <div>
          <Skeleton width="100px" height="14px" class="mb-1" />
          <Skeleton width="100%" height="36px" rounded="rounded" />
        </div>
      </div>
      <div class="card-elevated p-5 space-y-3">
        <Skeleton width="200px" height="20px" class="mb-3" />
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr>
                <th class="text-left px-2 py-1.5">
                  <Skeleton width="60px" height="12px" />
                </th>
                <th class="text-left px-2 py-1.5">
                  <Skeleton width="80px" height="12px" />
                </th>
                <th class="text-left px-2 py-1.5">
                  <Skeleton width="60px" height="12px" />
                </th>
                <th class="text-right px-2 py-1.5">
                  <Skeleton width="50px" height="12px" />
                </th>
                <th class="text-right px-2 py-1.5">
                  <Skeleton width="50px" height="12px" />
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="g in 3" :key="g" class="border-t border-mushroom-100 dark:border-mushroom-700/50">
                <td class="px-2 py-1.5"><Skeleton width="70px" height="12px" /></td>
                <td class="px-2 py-1.5"><Skeleton width="120px" height="12px" /></td>
                <td class="px-2 py-1.5"><Skeleton width="80px" height="12px" /></td>
                <td class="text-right px-2 py-1.5"><Skeleton width="60px" height="12px" /></td>
                <td class="text-center px-2 py-1.5"><Skeleton width="40px" height="12px" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-else-if="activeTab === 'bank'" class="space-y-4">
      <div class="card-elevated p-5 space-y-3">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label class="label-text">Bank</label>
            <select v-model="bank" class="select-field">
              <option v-for="opt in bankOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
          <div>
            <label class="label-text">CSV File</label>
            <input type="file" accept=".csv,.pdf" @change="handleBankFileChange" class="input-field file:mr-3 file:py-1 file:px-2 file:rounded file:border-0 file:bg-kangkong-50 dark:file:bg-kangkong-500/10 file:text-kangkong-700 dark:file:text-kangkong-400 file:text-xs file:font-medium" />
          </div>
        </div>

        <div>
          <label class="label-text">Import to Account</label>
          <select v-model="bankAccountId" class="select-field">
            <option value="" disabled>Select account</option>
            <template v-for="(accs, type) in groupedAccounts" :key="type">
              <optgroup :label="type.replace('_', ' ')">
                <option v-for="a in accs" :key="a.id" :value="a.id">{{ a.name }}</option>
              </optgroup>
            </template>
          </select>
        </div>

        <div class="flex gap-2">
          <button @click="handleBankPreview" :disabled="!bankFile || bankLoading" class="btn-primary disabled:opacity-50 text-xs">
            {{ bankLoading ? 'Parsing...' : 'Preview' }}
          </button>
          <button v-if="bankPreview" @click="resetBank" class="btn-ghost text-xs">Reset</button>
        </div>

        <div v-if="bankError" class="bg-tomato-50 dark:bg-tomato-500/10 text-tomato-700 dark:text-tomato-400 p-2.5 rounded text-xs">
          {{ bankError }}
        </div>
      </div>

      <div v-if="bankPreview" class="card-elevated p-5 space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-medium text-mushroom-700 dark:text-mushroom-300">Preview — {{ bankPreview.bank.toUpperCase() }}</h3>
          <div class="flex gap-3 text-xs">
            <span class="text-kangkong-700 dark:text-kangkong-400">Income: {{ bankPreview.total_income.toLocaleString() }}</span>
            <span class="text-tomato-600 dark:text-tomato-400">Expense: {{ bankPreview.total_expense.toLocaleString() }}</span>
            <span class="text-mushroom-400">{{ bankPreview.total_rows }} rows</span>
          </div>
        </div>

        <div class="overflow-x-auto max-h-80 overflow-y-auto">
          <table class="w-full text-xs">
            <thead class="sticky top-0 bg-mushroom-50 dark:bg-mushroom-800">
              <tr>
                <th class="text-left px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">Date</th>
                <th class="text-left px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">Description</th>
                <th class="text-left px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">Category</th>
                <th class="text-right px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">Amount</th>
                <th class="text-center px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">Type</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in bankPreview.rows" :key="i" class="border-t border-mushroom-100 dark:border-mushroom-700/50">
                <td class="px-2 py-1.5 text-mushroom-700 dark:text-mushroom-300">{{ row.date }}</td>
                <td class="px-2 py-1.5 text-mushroom-700 dark:text-mushroom-300 max-w-[200px] truncate" :title="row.description">{{ row.description }}</td>
                <td class="px-2 py-1.5">
                  <select v-model="row.category" class="bg-transparent border-b border-dashed border-mushroom-300 dark:border-mushroom-600 text-mushroom-700 dark:text-mushroom-300 text-xs focus:outline-none focus:border-kangkong-500 py-0.5 w-full">
                    <option v-for="c in expenseCategories" :key="c.id" :value="c.name">{{ c.name }}</option>
                  </select>
                </td>
                <td class="px-2 py-1.5 text-right font-medium" :class="row.type === 'income' ? 'text-kangkong-700 dark:text-kangkong-400' : 'text-tomato-600 dark:text-tomato-400'">
                  {{ row.type === 'income' ? '+' : '-' }}{{ row.amount.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}
                </td>
                <td class="px-2 py-1.5 text-center">
                  <span :class="row.type === 'income' ? 'bg-kangkong-50 dark:bg-kangkong-500/15 text-kangkong-700 dark:text-kangkong-400' : 'bg-tomato-50 dark:bg-tomato-500/15 text-tomato-600 dark:text-tomato-400'" class="px-1.5 py-0.5 rounded text-xs">
                    {{ row.type }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex gap-2 pt-1">
          <button @click="handleBankImport" :disabled="bankLoading || !bankAccountId" class="btn-secondary text-xs disabled:opacity-50">
            {{ bankLoading ? 'Importing...' : 'Import All' }}
          </button>
          <button @click="resetBank" class="btn-ghost text-xs">Cancel</button>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'bulk'" class="space-y-4">
      <div class="card-elevated p-5 space-y-3">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs text-mushroom-600 dark:text-mushroom-400">Upload a CSV file with your transactions. Download the template and legend for valid values.</p>
          </div>
          <div class="flex gap-2">
            <button @click="downloadLegend" class="px-3 py-1.5 text-xs bg-mushroom-100 dark:bg-mushroom-800 text-mushroom-600 dark:text-mushroom-400 rounded-lg hover:bg-mushroom-200 transition-colors font-medium whitespace-nowrap">
              Download Legend
            </button>
            <button @click="downloadTemplate" class="px-3 py-1.5 text-xs bg-mushroom-100 dark:bg-mushroom-800 text-mushroom-600 dark:text-mushroom-400 rounded-lg hover:bg-mushroom-200 transition-colors font-medium whitespace-nowrap">
              Download Template
            </button>
          </div>
        </div>

        <div>
          <label class="label-text">CSV File</label>
          <input type="file" accept=".csv" @change="handleBulkFileChange" class="input-field file:mr-3 file:py-1 file:px-2 file:rounded file:border-0 file:bg-kangkong-50 dark:file:bg-kangkong-500/10 file:text-kangkong-700 dark:file:text-kangkong-400 file:text-xs file:font-medium" />
        </div>

        <div class="flex gap-2">
          <button @click="handleBulkPreview" :disabled="!bulkFile || bulkLoading" class="btn-primary disabled:opacity-50 text-xs">
            {{ bulkLoading ? 'Parsing...' : 'Preview' }}
          </button>
          <button v-if="bulkPreview" @click="resetBulk" class="btn-ghost text-xs">Reset</button>
        </div>

        <div v-if="bulkError" class="bg-tomato-50 dark:bg-tomato-500/10 text-tomato-700 dark:text-tomato-400 p-2.5 rounded text-xs whitespace-pre-line">
          {{ bulkError }}
        </div>
      </div>

      <div v-if="bulkPreview" class="card-elevated p-5 space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-medium text-mushroom-700 dark:text-mushroom-300">Preview</h3>
          <div class="flex gap-3 text-xs">
            <span v-if="flaggedCount > 0" class="text-mango-600 dark:text-mango-400 font-medium">{{ flaggedCount }} flagged</span>
            <span class="text-kangkong-700 dark:text-kangkong-400">Income: {{ bulkPreview.total_income.toLocaleString() }}</span>
            <span class="text-tomato-600 dark:text-tomato-400">Expense: {{ bulkPreview.total_expense.toLocaleString() }}</span>
            <span class="text-mushroom-400">{{ bulkPreview.total_rows }} rows</span>
          </div>
        </div>

        <div v-if="bulkPreview.errors.length" class="bg-tomato-50 dark:bg-tomato-500/10 text-tomato-700 dark:text-tomato-400 p-2.5 rounded text-xs space-y-1">
          <div v-for="(err, i) in bulkPreview.errors" :key="i">{{ err }}</div>
        </div>

        <div v-if="flaggedCount > 0" class="bg-mango-50 dark:bg-mango-500/10 text-mango-700 dark:text-mango-400 p-2.5 rounded text-xs">
          {{ flaggedCount }} rows were auto-corrected or have warnings. Rows with orange highlights need your review.
        </div>

        <div class="overflow-x-auto max-h-96 overflow-y-auto">
          <table class="w-full text-xs">
            <thead class="sticky top-0 bg-mushroom-50 dark:bg-mushroom-800">
              <tr>
                <th class="text-left px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400 w-6"></th>
                <th class="text-left px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">Date</th>
                <th class="text-left px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">Account</th>
                <th class="text-left px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">Category</th>
                <th class="text-right px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">Amount</th>
                <th class="text-center px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">Type</th>
                <th class="text-left px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">Description</th>
                <th class="text-left px-2 py-1.5 font-medium text-mushroom-500 dark:text-mushroom-400">Sub-Account</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in bulkPreview.rows" :key="i"
                class="border-t border-mushroom-100 dark:border-mushroom-700/50"
                :class="row.warnings?.length ? 'bg-mango-50/50 dark:bg-mango-500/10' : ''">
                <td class="px-1 py-1.5">
                  <button @click="removeRow(i)" class="text-mushroom-400 hover:text-tomato-600 transition-colors" title="Remove row">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
                  </button>
                </td>
                <td class="px-2 py-1.5 text-mushroom-700 dark:text-mushroom-300">{{ row.date }}</td>
                <td class="px-2 py-1.5">
                  <div class="flex items-center gap-1">
                    <input v-model="row.account_id" class="bg-transparent border-b border-dashed border-mushroom-300 dark:border-mushroom-600 text-mushroom-700 dark:text-mushroom-300 text-xs w-full focus:outline-none focus:border-kangkong-500" :class="getWarningFor(row, 'Account') ? 'text-mango-700' : ''" />
                  </div>
                  <div v-if="getWarningFor(row, 'Account')" class="flex items-center gap-1 mt-0.5">
                    <span class="text-[10px] text-mango-600 truncate">{{ getWarningFor(row, 'Account') }}</span>
                    <button v-if="getSuggestion(getWarningFor(row, 'Account'))" @click="acceptSuggestion(row, 'Account', getWarningFor(row, 'Account'))" class="text-[10px] text-kangkong-600 hover:text-kangkong-800 font-medium whitespace-nowrap">Accept</button>
                    <button @click="dismissWarning(row, getWarningFor(row, 'Account'))" class="text-[10px] text-mushroom-400 hover:text-tomato-600 whitespace-nowrap">Dismiss</button>
                  </div>
                </td>
                <td class="px-2 py-1.5">
                  <div class="flex items-center gap-1">
                    <input v-model="row.category" class="bg-transparent border-b border-dashed border-mushroom-300 dark:border-mushroom-600 text-mushroom-700 dark:text-mushroom-300 text-xs w-full focus:outline-none focus:border-kangkong-500" :class="getWarningFor(row, 'Category') ? 'text-mango-700' : ''" />
                  </div>
                  <div v-if="getWarningFor(row, 'Category')" class="flex items-center gap-1 mt-0.5">
                    <span class="text-[10px] text-mango-600 truncate">{{ getWarningFor(row, 'Category') }}</span>
                    <button v-if="getSuggestion(getWarningFor(row, 'Category'))" @click="acceptSuggestion(row, 'Category', getWarningFor(row, 'Category'))" class="text-[10px] text-kangkong-600 hover:text-kangkong-800 font-medium whitespace-nowrap">Accept</button>
                    <button @click="dismissWarning(row, getWarningFor(row, 'Category'))" class="text-[10px] text-mushroom-400 hover:text-tomato-600 whitespace-nowrap">Dismiss</button>
                  </div>
                </td>
                <td class="px-2 py-1.5 text-right font-medium" :class="row.type === 'income' ? 'text-kangkong-700 dark:text-kangkong-400' : 'text-tomato-600 dark:text-tomato-400'">
                  {{ row.type === 'income' ? '+' : '-' }}{{ row.amount.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}
                </td>
                <td class="px-2 py-1.5 text-center">
                  <span :class="row.type === 'income' ? 'bg-kangkong-50 dark:bg-kangkong-500/15 text-kangkong-700 dark:text-kangkong-400' : 'bg-tomato-50 dark:bg-tomato-500/15 text-tomato-600 dark:text-tomato-400'" class="px-1.5 py-0.5 rounded text-xs">
                    {{ row.type }}
                  </span>
                </td>
                <td class="px-2 py-1.5 text-mushroom-700 dark:text-mushroom-300">{{ row.description }}</td>
                <td class="px-2 py-1.5">
                  <div class="flex items-center gap-1">
                    <input v-model="row.sub_account_id" class="bg-transparent border-b border-dashed border-mushroom-300 dark:border-mushroom-600 text-mushroom-700 dark:text-mushroom-300 text-xs w-full focus:outline-none focus:border-kangkong-500" :class="getWarningFor(row, 'Sub-account') ? 'text-mango-700' : ''" placeholder="—" />
                  </div>
                  <div v-if="getWarningFor(row, 'Sub-account')" class="flex items-center gap-1 mt-0.5">
                    <span class="text-[10px] text-mango-600 truncate">{{ getWarningFor(row, 'Sub-account') }}</span>
                    <button v-if="getSuggestion(getWarningFor(row, 'Sub-account'))" @click="acceptSuggestion(row, 'Sub-account', getWarningFor(row, 'Sub-account'))" class="text-[10px] text-kangkong-600 hover:text-kangkong-800 font-medium whitespace-nowrap">Accept</button>
                    <button @click="dismissWarning(row, getWarningFor(row, 'Sub-account'))" class="text-[10px] text-mushroom-400 hover:text-tomato-600 whitespace-nowrap">Dismiss</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex gap-2 pt-1">
          <button v-if="flaggedCount > 0" @click="acceptAllSuggestions(bulkPreview.rows)" class="btn-ghost text-xs text-kangkong-600 hover:text-kangkong-800">
            Accept All Suggestions
          </button>
          <button @click="handleBulkImport" :disabled="bulkLoading || bulkPreview.rows.length === 0" class="btn-secondary text-xs disabled:opacity-50">
            {{ bulkLoading ? 'Importing...' : 'Import All' }}
          </button>
          <button @click="resetBulk" class="btn-ghost text-xs">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>
