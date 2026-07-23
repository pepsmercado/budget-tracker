<script setup>
import Sidebar from './components/Sidebar.vue'
import TopBar from './components/TopBar.vue'
</script>

<template>
  <div class="flex h-screen bg-[#fbfcfa]">
    <Sidebar />
    <div class="flex-1 flex flex-col overflow-hidden">
      <TopBar />
      <main class="flex-1 overflow-y-auto p-5">
        <router-view />
      </main>
    </div>
  </div>
</template>
