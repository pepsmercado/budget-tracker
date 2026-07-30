<script setup>
import { ref, computed, inject, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SidebarIcon from './SidebarIcon.vue'

const route = useRoute()
const router = useRouter()
const collapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')
const sidebarOpen = inject('sidebarOpen')
const hoveredGroup = ref(null)
const flyoutItems = ref([])
const flyoutStyle = ref({})
const flyoutLabel = ref('')
let hoverTimeout = null

function closeMobile() {
  sidebarOpen.value = false
}

function toggle() {
  collapsed.value = !collapsed.value
  localStorage.setItem('sidebar-collapsed', collapsed.value)
}

const activeCurrency = computed(() => {
  if (route.path.startsWith('/usd')) return 'usd'
  return 'php'
})

function switchCurrency(c) {
  const newPath = route.path.replace(/^\/(usd|php)/, `/${c}`)
  router.push(newPath)
  closeMobile()
}

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

function menuFor(currency) {
  const prefix = `/${currency}`
  return [
    { to: `${prefix}`, label: 'Dashboard', icon: 'dashboard' },
    {
      key: 'transactions',
      label: 'Transactions',
      icon: 'transactions',
      children: [
        { to: `${prefix}/transactions`, label: 'All Transactions', icon: 'transactions' },
        { to: `${prefix}/transactions/new`, label: 'Add Record', icon: 'add' },
        { to: `${prefix}/transfers`, label: 'Transfers', icon: 'transfers' },
        { to: `${prefix}/upload`, label: 'Bulk Upload', icon: 'upload' },
      ]
    },
    {
      key: 'planning',
      label: 'Planning',
      icon: 'budgets',
      children: [
        { to: `${prefix}/budgets`, label: 'Budgets', icon: 'budgets' },
        { to: `${prefix}/accounts`, label: 'Accounts', icon: 'accounts' },
        { to: `${prefix}/recurring`, label: 'Recurring', icon: 'recurring' },
      ]
    },
    { to: `${prefix}/reports`, label: 'Reports', icon: 'reports' },
  ]
}

function isActive(linkTo) {
  if (linkTo === `/${activeCurrency.value}`) {
    return route.path === linkTo || route.path === linkTo + '/'
  }
  return route.path === linkTo
}

function onGroupEnter(key, event, item) {
  clearTimeout(hoverTimeout)
  const rect = event.currentTarget.getBoundingClientRect()
  flyoutItems.value = item.children
  flyoutLabel.value = item.label
  flyoutStyle.value = {
    position: 'fixed',
    top: rect.top + 'px',
    left: (rect.right - 2) + 'px',
  }
  hoveredGroup.value = key
}

function onFlyoutEnter() {
  clearTimeout(hoverTimeout)
}

function onGroupLeave() {
  hoverTimeout = setTimeout(() => {
    hoveredGroup.value = null
  }, 200)
}

function expandSidebar() {
  if (collapsed.value) {
    localStorage.setItem('sidebar-collapsed', 'false')
    collapsed.value = false
  }
}

function onCollapsedItemClick(item) {
  expandSidebar()
  if (item.children) {
    const list = expanded.value[activeCurrency.value]
    if (!list.includes(item.key)) {
      list.push(item.key)
      saveExpanded(activeCurrency.value)
    }
  }
}

watch(() => route.path, (path) => {
  const items = menuFor(activeCurrency.value)
  for (const item of items) {
    if (item.children && item.children.some(c => path === c.to || path === c.to + '/')) {
      const list = expanded.value[activeCurrency.value]
      if (!list.includes(item.key)) {
        list.push(item.key)
        saveExpanded(activeCurrency.value)
      }
    }
  }
}, { immediate: true })

onBeforeUnmount(() => clearTimeout(hoverTimeout))
</script>

<template>
  <aside
    class="bg-[#1c1b1b] text-white flex flex-col transition-all duration-200 ease-in-out h-full"
    :class="collapsed ? 'w-14' : 'w-56'"
  >
    <div class="p-4 border-b border-white/10">
      <div class="flex items-center gap-2.5 cursor-pointer" @click="router.push('/usd'); closeMobile()">
        <div class="w-8 h-8 rounded-lg overflow-hidden flex-shrink-0">
          <img src="/favicon.png" alt="Logo" class="w-full h-full object-cover" />
        </div>
        <h1 v-if="!collapsed" class="font-semibold text-sm whitespace-nowrap">Peps Budget Tracker</h1>
      </div>
    </div>

    <nav class="flex-1 p-2 overflow-y-auto">
      <!-- Currency tabs -->
      <div v-if="!collapsed" class="flex mb-3 rounded-lg bg-white/5 p-0.5">
        <button
          v-for="c in ['usd', 'php']"
          :key="c"
          @click="switchCurrency(c)"
          class="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-xs font-medium transition-colors"
          :class="activeCurrency === c ? 'bg-white/15 text-white' : 'text-white/70 hover:text-white'"
        >
          <span>{{ c === 'usd' ? '🇺🇸' : '🇵🇭' }}</span>
          <span>{{ c.toUpperCase() }}</span>
        </button>
      </div>
      <button
        v-if="collapsed"
        @click="switchCurrency(activeCurrency === 'usd' ? 'php' : 'usd')"
        class="w-full flex items-center justify-center py-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors mb-2"
        :title="activeCurrency === 'usd' ? 'Switch to PHP' : 'Switch to USD'"
      >
        <span class="text-lg">{{ activeCurrency === 'usd' ? '🇺🇸' : '🇵🇭' }}</span>
      </button>

      <template v-for="item in menuFor(activeCurrency)" :key="item.label">
        <!-- Top-level link -->
        <router-link
          v-if="!item.children"
          :to="item.to"
          class="sidebar-link sidebar-link-parent"
          :class="isActive(item.to) ? 'active' : ''"
          :title="collapsed ? item.label : ''"
          @click="expandSidebar(); closeMobile()"
        >
          <SidebarIcon :name="item.icon" class="flex-shrink-0" />
          <span v-if="!collapsed" class="whitespace-nowrap overflow-hidden text-ellipsis">{{ item.label }}</span>
        </router-link>

        <!-- Group with children -->
        <template v-else>
          <div class="relative" @mouseenter="collapsed ? onGroupEnter(item.key, $event, item) : null" @mouseleave="collapsed ? onGroupLeave() : null">
            <button
              @click="collapsed ? onCollapsedItemClick(item) : toggleGroup(activeCurrency, item.key)"
              class="sidebar-link sidebar-link-parent w-full"
              :class="[
                item.children.some(c => isActive(c.to)) ? 'active' : '',
                collapsed ? 'justify-center cursor-default' : ''
              ]"
              :title="collapsed ? item.label : ''"
            >
              <SidebarIcon :name="item.icon" class="flex-shrink-0" />
              <template v-if="!collapsed">
                <span class="whitespace-nowrap overflow-hidden text-ellipsis flex-1 text-left">{{ item.label }}</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                  class="flex-shrink-0 transition-transform duration-150"
                  :class="isExpanded(activeCurrency, item.key) ? 'rotate-90' : ''"
                ><path d="M9 18l6-6-6-6"/></svg>
              </template>
            </button>

            <div v-if="!collapsed && isExpanded(activeCurrency, item.key)" class="ml-3 space-y-0.5">
              <router-link
                v-for="child in item.children"
                :key="child.to"
                :to="child.to"
                class="flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-colors cursor-pointer"
                :class="isActive(child.to) ? 'text-white font-medium bg-white/10' : 'text-white/70 hover:text-white hover:bg-white/5'"
                @click="closeMobile"
              >
                <SidebarIcon :name="child.icon" class="flex-shrink-0 opacity-60" />
                <span class="whitespace-nowrap overflow-hidden text-ellipsis">{{ child.label }}</span>
              </router-link>
            </div>
          </div>
        </template>
      </template>
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

  <Teleport to="body">
    <div
      v-if="collapsed && hoveredGroup"
      :style="flyoutStyle"
      class="w-50 py-1 bg-mushroom-800 border border-white/10 rounded-lg shadow-xl z-[9999]"
      @mouseenter="onFlyoutEnter()"
      @mouseleave="onGroupLeave()"
      style="margin-left: -2px; padding-left: 2px;"
    >
      <div class="px-3 py-1.5 text-[10px] font-medium text-white/40 uppercase tracking-wider">{{ flyoutLabel }}</div>
      <router-link
        v-for="child in flyoutItems"
        :key="child.to"
        :to="child.to"
        class="flex items-center gap-2.5 px-3 py-2 text-sm transition-colors cursor-pointer"
        :class="isActive(child.to) ? 'text-white font-medium bg-white/10' : 'text-white/80 hover:text-white hover:bg-white/8'"
        @click="closeMobile"
      >
        <SidebarIcon :name="child.icon" class="flex-shrink-0 opacity-70" />
        <span class="whitespace-nowrap">{{ child.label }}</span>
      </router-link>
    </div>
  </Teleport>
</template>
