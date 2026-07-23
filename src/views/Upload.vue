<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import CategoryBadge from '../components/CategoryBadge.vue'

const router = useRouter()

const file = ref(null)
const bank = ref('auto')
const preview = ref(null)
const loading = ref(false)
const error = ref('')
const importing = ref(false)
const imported = ref(false)

const bankOptions = [
  { value: 'auto', label: 'Auto-detect' },
  { value: 'bpi', label: 'BPI' },
  { value: 'bdo', label: 'BDO' },
  { value: 'maya', label: 'Maya' },
  { value: 'bank_of_america', label: 'Bank of America' },
]

function handleFileChange(e) {
  file.value = e.target.files[0]
  preview.value = null
  error.value = ''
  imported.value = false
}

async function handlePreview() {
  if (!file.value) return
  loading.value = true
  error.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file.value)
    formData.append('bank', bank.value)
    const { data } = await api.post('/upload/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    preview.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to parse CSV'
  } finally {
    loading.value = false
  }
}

function reset() {
  file.value = null
  preview.value = null
  error.value = ''
  imported.value = false
}
</script>

<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-extrabold text-charcoal">Upload Bank Statement</h2>

    <div class="card-elevated p-6 space-y-4">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="label-text">Bank</label>
          <select v-model="bank" class="select-field">
            <option v-for="opt in bankOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <div>
          <label class="label-text">CSV File</label>
          <input type="file" accept=".csv" @change="handleFileChange" class="input-field file:mr-4 file:py-1 file:px-3 file:rounded-lg file:border-0 file:bg-coral/10 file:text-coral file:font-bold file:text-sm" />
        </div>
      </div>

      <div class="flex gap-3">
        <button @click="handlePreview" :disabled="!file || loading" class="btn-primary disabled:opacity-50">
          {{ loading ? 'Parsing...' : 'Preview' }}
        </button>
        <button v-if="preview" @click="reset" class="btn-ghost">Reset</button>
      </div>

      <div v-if="error" class="bg-coral/10 text-coral-dark p-3 rounded-xl text-sm font-semibold">
        {{ error }}
      </div>
    </div>

    <div v-if="preview" class="card-elevated p-6 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="font-bold text-charcoal">Preview — {{ preview.bank.toUpperCase() }}</h3>
        <div class="flex gap-4 text-sm font-semibold">
          <span class="text-sage-dark">Income: {{ preview.total_income.toLocaleString() }}</span>
          <span class="text-coral">Expense: {{ preview.total_expense.toLocaleString() }}</span>
          <span class="text-charcoal-light">{{ preview.total_rows }} rows</span>
        </div>
      </div>

      <div class="overflow-x-auto max-h-96 overflow-y-auto">
        <table class="w-full text-sm">
          <thead class="sticky top-0 bg-cream">
            <tr>
              <th class="text-left px-3 py-2 font-bold text-charcoal-light">Date</th>
              <th class="text-left px-3 py-2 font-bold text-charcoal-light">Description</th>
              <th class="text-right px-3 py-2 font-bold text-charcoal-light">Amount</th>
              <th class="text-center px-3 py-2 font-bold text-charcoal-light">Type</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in preview.rows" :key="i" class="border-t border-cream-dark hover:bg-cream/30">
              <td class="px-3 py-2 text-charcoal">{{ row.date }}</td>
              <td class="px-3 py-2 text-charcoal">{{ row.description }}</td>
              <td class="px-3 py-2 text-right font-semibold" :class="row.type === 'income' ? 'text-sage-dark' : 'text-coral'">
                {{ row.type === 'income' ? '+' : '-' }}{{ row.amount.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}
              </td>
              <td class="px-3 py-2 text-center">
                <span :class="row.type === 'income' ? 'bg-sage/15 text-sage-dark' : 'bg-coral/15 text-coral'" class="px-2 py-0.5 rounded-full text-xs font-bold">
                  {{ row.type }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="flex gap-3 pt-2">
        <button class="btn-secondary">Import All</button>
        <button class="btn-ghost">Cancel</button>
      </div>
    </div>
  </div>
</template>
