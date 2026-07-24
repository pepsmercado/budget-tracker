<script setup>
import { useToast } from '../composables/useToast.js'
const { toasts, dismiss } = useToast()

function colorClass(type) {
  switch (type) {
    case 'success': return 'bg-kangkong-600 text-white'
    case 'error': return 'bg-tomato-600 text-white'
    case 'warning': return 'bg-mango-500 text-mushroom-950'
    default: return 'bg-mushroom-800 text-white'
  }
}
</script>

<template>
  <div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none" style="max-width: 360px">
    <TransitionGroup
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="['pointer-events-auto rounded-lg px-4 py-2.5 text-sm font-medium shadow-lg flex items-start gap-2', colorClass(toast.type)]"
      >
        <span class="flex-1">{{ toast.message }}</span>
        <button @click="dismiss(toast.id)" class="text-white/70 hover:text-white text-xs mt-0.5">&times;</button>
      </div>
    </TransitionGroup>
  </div>
</template>
