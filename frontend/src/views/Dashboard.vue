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
        borderColor: '#81B29A',
        backgroundColor: 'rgba(129, 178, 154, 0.15)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#81B29A',
      },
      {
        label: 'Expense',
        data: summary.value.monthly.map(m => m.expense),
        borderColor: '#E07A5F',
        backgroundColor: 'rgba(224, 122, 95, 0.15)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#E07A5F',
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
      backgroundColor: ['#E07A5F', '#81B29A', '#F2A68E', '#A8D4BB', '#DDA0DD', '#87CEEB', '#B0C4DE'],
      borderWidth: 0,
      hoverOffset: 8,
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
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-extrabold text-charcoal">Dashboard</h2>
      <span class="text-charcoal-light text-sm font-semibold">{{ currentYear }}</span>
    </div>

    <div v-if="summary" class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="card-elevated p-6">
        <h3 class="font-bold text-charcoal mb-4">Monthly Trend</h3>
        <Line :data="monthlyChartData" :options="{ responsive: true, plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } } }, scales: { y: { grid: { color: '#EDE4CC' } }, x: { grid: { display: false } } } }" />
      </div>

      <div class="card-elevated p-6">
        <h3 class="font-bold text-charcoal mb-4">Expense by Group</h3>
        <Doughnut :data="groupChartData" :options="{ responsive: true, plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 12 } } }, cutout: '65%' }" />
      </div>
    </div>

    <div v-if="summary" class="card-elevated p-6">
      <h3 class="font-bold text-charcoal mb-4">Expense Breakdown</h3>
      <div class="space-y-4">
        <div v-for="section in categoryBreakdown" :key="section.group">
          <div class="text-sm font-bold text-charcoal-light mb-2">{{ section.group }}</div>
          <div class="space-y-1">
            <div v-for="cat in section.categories" :key="cat.category" class="flex items-center justify-between text-sm">
              <span class="text-charcoal">{{ cat.category }}</span>
              <span class="font-semibold text-charcoal">{{ cat.currency }} {{ cat.total.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div>
      <h3 class="font-bold text-charcoal mb-3">Accounts</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div v-for="b in balances" :key="b.account_id" class="card p-4 hover:shadow-md transition-shadow">
          <div class="text-sm text-charcoal-light font-semibold">{{ b.account_name }}</div>
          <div class="text-xl font-extrabold text-charcoal mt-1">
            {{ b.currency }} {{ b.balance.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
