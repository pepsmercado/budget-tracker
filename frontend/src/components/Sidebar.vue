<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
const links = [
  { to: '/', label: 'Dashboard', icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>` },
  { to: '/transactions', label: 'Transactions', icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 14l2 2 4-4"/></svg>` },
  { to: '/transactions/new', label: 'Add Record', icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/></svg>` },
  { to: '/upload', label: 'Upload Statement', icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>` },
  { to: '/budgets', label: 'Budgets', icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M16 8l-8 8"/><path d="M8 8h8v8"/></svg>` },
  { to: '/accounts', label: 'Accounts', icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12V7H5a2 2 0 010-4h14v4"/><path d="M3 5v14a2 2 0 002 2h16v-5"/><path d="M18 12a2 2 0 000 4h4v-4h-4z"/></svg>` },
]
</script>

<template>
  <aside class="w-64 bg-charcoal flex flex-col">
    <div class="p-5 border-b border-white/10">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-coral flex items-center justify-center text-white font-extrabold text-lg">
          P
        </div>
        <div>
          <h1 class="text-white font-extrabold text-base leading-tight">Expense Tracker</h1>
          <p class="text-white/50 text-xs">Personal Finance</p>
        </div>
      </div>
    </div>
    <nav class="flex-1 p-4 space-y-1">
      <router-link
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        class="sidebar-link"
        :class="route.path === link.to ? 'active' : ''"
      >
        <span v-html="link.icon"></span>
        <span>{{ link.label }}</span>
      </router-link>
    </nav>
    <div class="p-4 border-t border-white/10">
      <div class="text-white/40 text-xs text-center">v1.0 — Mock Data</div>
    </div>
  </aside>
</template>
