<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()

const file = ref(null)
const bank = ref('auto')
const preview = ref(null)
const loading = ref(false)
const error = ref('')
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
  <div class="space-y-5">
    <h2 class="text-lg font-medium text-mushroom-950">Upload Bank Statement</h2>

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
          <input type="file" accept=".csv" @change="handleFileChange" class="input-field file:mr-3 file:py-1 file:px-2 file:rounded file:border-0 file:bg-kangkong-50 file:text-kangkong-700 file:text-xs file:font-medium" />
        </div>
      </div>

      <div class="flex gap-2">
        <button @click="handlePreview" :disabled="!file || loading" class="btn-primary disabled:opacity-50 text-xs">
          {{ loading ? 'Parsing...' : 'Preview' }}
        </button>
        <button v-if="preview" @click="reset" class="btn-ghost text-xs">Reset</button>
      </div>

      <div v-if="error" class="bg-tomato-50 text-tomato-700 p-2.5 rounded text-xs">
        {{ error }}
      </div>
    </div>

    <div v-if="preview" class="card-elevated p-5 space-y-3">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-medium text-mushroom-700">Preview — {{ preview.bank.toUpperCase() }}</h3>
        <div class="flex gap-3 text-xs">
          <span class="text-kangkong-700">Income: {{ preview.total_income.toLocaleString() }}</span>
          <span class="text-tomato-600">Expense: {{ preview.total_expense.toLocaleString() }}</span>
          <span class="text-mushroom-400">{{ preview.total_rows }} rows</span>
        </div>
      </div>

      <div class="overflow-x-auto max-h-80 overflow-y-auto">
        <table class="w-full text-xs">
          <thead class="sticky top-0 bg-mushroom-50">
            <tr>
              <th class="text-left px-3 py-1.5 font-medium text-mushroom-500">Date</th>
              <th class="text-left px-3 py-1.5 font-medium text-mushroom-500">Description</th>
              <th class="text-right px-3 py-1.5 font-medium text-mushroom-500">Amount</th>
              <th class="text-center px-3 py-1.5 font-medium text-mushroom-500">Type</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in preview.rows" :key="i" class="border-t border-mushroom-100">
              <td class="px-3 py-1.5 text-mushroom-700">{{ row.date }}</td>
              <td class="px-3 py-1.5 text-mushroom-700">{{ row.description }}</td>
              <td class="px-3 py-1.5 text-right font-medium" :class="row.type === 'income' ? 'text-kangkong-700' : 'text-tomato-600'">
                {{ row.type === 'income' ? '+' : '-' }}{{ row.amount.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}
              </td>
              <td class="px-3 py-1.5 text-center">
                <span :class="row.type === 'income' ? 'bg-kangkong-50 text-kangkong-700' : 'bg-tomato-50 text-tomato-600'" class="px-1.5 py-0.5 rounded text-xs">
                  {{ row.type }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="flex gap-2 pt-1">
        <button class="btn-secondary text-xs">Import All</button>
        <button class="btn-ghost text-xs">Cancel</button>
      </div>
    </div>
  </div>
</template>
