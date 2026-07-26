<script setup>
import { ref, provide, computed } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
import TopBar from './components/TopBar.vue'
import ToastContainer from './components/ToastContainer.vue'
import AuthGate from './components/AuthGate.vue'

const route = useRoute()
const sidebarOpen = ref(false)
provide('sidebarOpen', sidebarOpen)

const fabLink = computed(() => {
  if (route.path.startsWith('/usd')) return '/usd/transactions/new'
  return '/php/transactions/new'
})
</script>

<template>
  <AuthGate>
    <div class="flex h-screen bg-[#fbfcfa] dark:bg-[#1a1e1e]">
      <!-- Mobile overlay -->
      <div
        v-if="sidebarOpen"
        class="fixed inset-0 bg-black/40 z-40 lg:hidden"
        @click="sidebarOpen = false"
      />

      <!-- Sidebar -->
      <div
        class="fixed inset-y-0 left-0 z-50 transform transition-transform duration-200 lg:relative lg:transform-none lg:h-full lg:shrink-0"
        :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'"
      >
        <Sidebar />
      </div>

      <!-- Main content -->
      <div class="flex-1 flex flex-col overflow-hidden min-w-0">
        <TopBar />
        <main class="flex-1 overflow-y-auto p-3 sm:p-5">
          <router-view />
        </main>
      </div>

      <!-- FAB -->
      <router-link
        :to="fabLink"
        class="fixed bottom-6 right-6 w-12 h-12 bg-kangkong-600 hover:bg-kangkong-700 dark:bg-blueberry-500 dark:hover:bg-blueberry-600 text-white rounded-full shadow-lg flex items-center justify-center transition-all z-50 hover:scale-110"
        title="Add Record"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </router-link>

      <ToastContainer />
    </div>
  </AuthGate>
</template>
