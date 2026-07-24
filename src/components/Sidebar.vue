<script setup>
import { ref, computed, inject } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const collapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')
const sidebarOpen = inject('sidebarOpen')

function closeMobile() {
  sidebarOpen.value = false
}

function toggle() {
  collapsed.value = !collapsed.value
  localStorage.setItem('sidebar-collapsed', collapsed.value)
}

const currentCurrency = computed(() => {
  if (route.path.startsWith('/usd')) return 'usd'
  return 'php'
})

// Flatten all links for active state checking
const allLinks = computed(() => {
  const links = []
  for (const currency of ['php', 'usd']) {
    for (const item of menuFor(currency)) {
      if (item.to) links.push(item.to)
      if (item.children) {
        for (const child of item.children) links.push(child.to)
      }
    }
  }
  return links
})

// Expanded groups state — stored per currency
const expanded = ref({
  php: JSON.parse(localStorage.getItem('sidebar-expanded-php') || '[]'),
  usd: JSON.parse(localStorage.getItem('sidebar-expanded-usd') || '[]'),
})

function saveExpanded(currency) {
  localStorage.setItem(`sidebar-expanded-${currency}`, JSON.stringify(expanded.value[currency]))
}

function toggleGroup(currency, key) {
  const list = expanded.value[currency]
  const idx = list.indexOf(key)
  if (idx >= 0) list.splice(idx, 1)
  else list.push(key)
  saveExpanded(currency)
}

function isExpanded(currency, key) {
  return expanded.value[currency]?.includes(key)
}

// Auto-expand group when a child route is active
function autoExpand(currency, item) {
  if (!item.children) return false
  const wasExpanded = isExpanded(currency, item.key)
  const shouldExpand = item.children.some(c => isActive(c.to))
  if (shouldExpand && !wasExpanded) {
    expanded.value[currency].push(item.key)
    saveExpanded(currency)
    return true
  }
  return wasExpanded
}

const iconDashboard = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>`
const iconTransactions = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 14l2 2 4-4"/></svg>`
const iconAdd = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>`
const iconUpload = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`
const iconBudget = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M16 8l-8 8"/><path d="M8 8h8v8"/></svg>`
const iconAccounts = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12V7H5a2 2 0 010-4h14v4"/><path d="M3 5v14a2 2 0 002 2h16v-5"/><path d="M18 12a2 2 0 000 4h4v-4h-4z"/></svg>`
const iconRecurring = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/><polyline points="21 3 21 9 15 9"/></svg>`
const iconTransfer = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4"/></svg>`
const iconReports = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>`
const iconChevron = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>`

function menuFor(currency) {
  const prefix = `/${currency}`
  return [
    { to: `${prefix}`, label: 'Dashboard', icon: iconDashboard },
    {
      key: 'transactions',
      label: 'Transactions',
      icon: iconTransactions,
      children: [
        { to: `${prefix}/transactions`, label: 'All Transactions', icon: iconTransactions },
        { to: `${prefix}/transactions/new`, label: 'Add Record', icon: iconAdd },
        { to: `${prefix}/transfers`, label: 'Transfers', icon: iconTransfer },
        { to: `${prefix}/upload`, label: 'Bulk Upload', icon: iconUpload },
      ]
    },
    {
      key: 'planning',
      label: 'Planning',
      icon: iconBudget,
      children: [
        { to: `${prefix}/budgets`, label: 'Budgets', icon: iconBudget },
        { to: `${prefix}/accounts`, label: 'Accounts', icon: iconAccounts },
        { to: `${prefix}/recurring`, label: 'Recurring', icon: iconRecurring },
      ]
    },
    { to: `${prefix}/reports`, label: 'Reports', icon: iconReports },
  ]
}

function isActive(linkTo) {
  if (linkTo === `/${currentCurrency.value}`) {
    return route.path === linkTo || route.path === linkTo + '/'
  }
  return route.path === linkTo || route.path.startsWith(linkTo + '/')
}
</script>

<template>
  <aside
    class="bg-mushroom-950 text-white flex flex-col transition-all duration-200 ease-in-out h-full"
    :class="collapsed ? 'w-14' : 'w-56'"
  >
    <div class="p-4 border-b border-white/10">
      <div class="flex items-center gap-2.5">
        <div class="w-8 h-8 rounded-lg bg-kangkong-600 flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
          P
        </div>
        <h1 v-if="!collapsed" class="font-semibold text-sm whitespace-nowrap">Expense Tracker</h1>
      </div>
    </div>

    <nav class="flex-1 p-2 overflow-y-auto space-y-3">
      <div v-for="currency in ['php', 'usd']" :key="currency">
        <div v-if="!collapsed" class="px-2 pt-1 pb-1">
          <span class="text-[10px] uppercase tracking-wider font-medium" :class="currentCurrency === currency ? 'text-kangkong-400' : 'text-white/30'">
            {{ currency === 'php' ? '🇵🇭 PHP' : '🇺🇸 USD' }}
          </span>
        </div>
        <div v-if="collapsed" class="border-t border-white/10 my-1"></div>

        <template v-for="item in menuFor(currency)" :key="item.label">
          <!-- Top-level link (no children) -->
          <router-link
            v-if="!item.children"
            :to="item.to"
            class="sidebar-link"
            :class="isActive(item.to) ? 'active' : ''"
            :title="collapsed ? item.label : ''"
            @click="closeMobile"
          >
            <span v-html="item.icon" class="flex-shrink-0"></span>
            <span v-if="!collapsed" class="whitespace-nowrap overflow-hidden text-ellipsis">{{ item.label }}</span>
          </router-link>

          <!-- Group with children -->
          <template v-else>
            <!-- Group header -->
            <button
              @click="collapsed ? null : toggleGroup(currency, item.key)"
              class="sidebar-link w-full"
              :class="[
                item.children.some(c => isActive(c.to)) ? 'active' : '',
                collapsed ? 'justify-center cursor-default' : ''
              ]"
              :title="collapsed ? item.label : ''"
            >
              <span v-html="item.icon" class="flex-shrink-0"></span>
              <template v-if="!collapsed">
                <span class="whitespace-nowrap overflow-hidden text-ellipsis flex-1 text-left">{{ item.label }}</span>
                <span
                  v-html="iconChevron"
                  class="flex-shrink-0 transition-transform duration-150"
                  :class="isExpanded(currency, item.key) ? 'rotate-90' : ''"
                />
              </template>
            </button>

            <!-- Children -->
            <div v-if="!collapsed && isExpanded(currency, item.key)" class="ml-3 space-y-0.5">
              <router-link
                v-for="child in item.children"
                :key="child.to"
                :to="child.to"
                class="flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-colors cursor-pointer"
                :class="isActive(child.to) ? 'text-kangkong-400 bg-white/5 font-medium' : 'text-white/60 hover:text-white hover:bg-white/5'"
                @click="closeMobile"
              >
                <span v-html="child.icon" class="flex-shrink-0 opacity-60"></span>
                <span class="whitespace-nowrap overflow-hidden text-ellipsis">{{ child.label }}</span>
              </router-link>
            </div>
          </template>
        </template>
      </div>
    </nav>

    <div class="p-2 border-t border-white/10">
      <button
        @click="toggle"
        class="w-full flex items-center justify-center gap-2 p-2 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors"
        :title="collapsed ? 'Expand' : 'Collapse'"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          class="flex-shrink-0 transition-transform duration-200"
          :class="collapsed ? 'rotate-180' : ''"
        >
          <path d="M11 19l-7-7 7-7M18 19l-7-7 7-7"/>
        </svg>
        <span v-if="!collapsed" class="text-xs whitespace-nowrap">Collapse</span>
      </button>
    </div>
  </aside>
</template>
