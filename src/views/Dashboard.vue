<script setup>
import { ref, onMounted, computed } from 'vue'
import { Line, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement,
  ArcElement, Title, Tooltip, Legend, Filler
} from 'chart.js'
import { useSummary } from '../composables/useSummary'
import api from '../api'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ArcElement, Title, Tooltip, Legend, Filler)

const { summary, balances, fetchSummary, fetchBalances } = useSummary()
const currentYear = new Date().getFullYear()
const categories = ref([])

onMounted(async () => {
  await Promise.all([fetchSummary(currentYear), fetchBalances(), fetchCategories()])
})

async function fetchCategories() {
  const { data } = await api.get('/categories')
  categories.value = data
}

const categoryToGroup = computed(() => {
  const map = {}
  for (const c of categories.value) {
    map[c.name] = c.group
  }
  return map
})

const monthlyChartData = computed(() => {
  if (!summary.value) return { labels: [], datasets: [] }
  return {
    labels: summary.value.monthly.map(m => m.month),
    datasets: [
      {
        label: 'Income',
        data: summary.value.monthly.map(m => m.income),
        borderColor: '#17ad49',
        backgroundColor: 'rgba(23, 173, 73, 0.08)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: '#17ad49',
      },
      {
        label: 'Expense',
        data: summary.value.monthly.map(m => m.expense),
        borderColor: '#da2f38',
        backgroundColor: 'rgba(218, 47, 56, 0.08)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: '#da2f38',
      },
    ],
  }
})

const groupChartData = computed(() => {
  if (!summary.value) return { labels: [], datasets: [] }
  const groups = {}
  for (const c of summary.value.by_category) {
    const group = categoryToGroup.value[c.category] || 'Other'
    if (!groups[group]) groups[group] = 0
    groups[group] += c.total
  }
  const sorted = Object.entries(groups).sort((a, b) => b[1] - a[1])
  return {
    labels: sorted.map(([g]) => g),
    datasets: [{
      data: sorted.map(([, v]) => v),
      backgroundColor: ['#da2f38', '#17ad49', '#8952f6', '#1679fa', '#ff970a', '#0592b5', '#738482'],
      borderWidth: 0,
      hoverOffset: 4,
    }],
  }
})

const categoryBreakdown = computed(() => {
  if (!summary.value) return []
  const groups = {}
  for (const c of summary.value.by_category) {
    const group = categoryToGroup.value[c.category] || 'Other'
    if (!groups[group]) groups[group] = []
    groups[group].push(c)
  }
  const result = []
  const order = ['Fixed', 'Essential', 'Lifestyle', 'Sinking', 'School', 'Income', 'Misc', 'Other']
  for (const g of order) {
    if (groups[g]) {
      result.push({ group: g, categories: groups[g].sort((a, b) => b.total - a.total) })
    }
  }
  return result
})
</script>

<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-medium text-mushroom-950">Dashboard</h2>
      <span class="text-xs text-mushroom-400">{{ currentYear }}</span>
    </div>

    <div v-if="summary" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="card-elevated p-5">
        <h3 class="text-sm font-medium text-mushroom-600 mb-3">Monthly Trend</h3>
        <Line :data="monthlyChartData" :options="{ responsive: true, plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 12, font: { size: 11 } } } }, scales: { y: { grid: { color: '#e6eaea' }, ticks: { font: { size: 11 } } }, x: { grid: { display: false }, ticks: { font: { size: 11 } } } } }" />
      </div>

      <div class="card-elevated p-5">
        <h3 class="text-sm font-medium text-mushroom-600 mb-3">Expense by Group</h3>
        <Doughnut :data="groupChartData" :options="{ responsive: true, plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 10, font: { size: 11 } } }, cutout: '65%' } }" />
      </div>
    </div>

    <div v-if="summary" class="card-elevated p-5">
      <h3 class="text-sm font-medium text-mushroom-600 mb-3">Expense Breakdown</h3>
      <div class="space-y-4">
        <div v-for="section in categoryBreakdown" :key="section.group">
          <div class="text-xs font-medium text-mushroom-400 uppercase tracking-wide mb-1.5">{{ section.group }}</div>
          <div class="space-y-1">
            <div v-for="cat in section.categories" :key="cat.category" class="flex items-center justify-between text-sm">
              <span class="text-mushroom-700">{{ cat.category }}</span>
              <span class="font-medium text-mushroom-950">{{ cat.currency }} {{ cat.total.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div>
      <h3 class="text-sm font-medium text-mushroom-600 mb-2">Accounts</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div v-for="b in balances" :key="b.account_id" class="card p-4">
          <div class="text-xs text-mushroom-400">{{ b.account_name }}</div>
          <div class="text-base font-semibold text-mushroom-950 mt-0.5">
            {{ b.currency }} {{ b.balance.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
