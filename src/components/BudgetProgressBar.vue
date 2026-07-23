<script setup>
const props = defineProps({ spent: Number, budget: Number })

const percentage = props.budget > 0 ? Math.min((props.spent / props.budget) * 100, 100) : 0
const colorClass = percentage < 60 ? 'bg-sage' : percentage < 85 ? 'bg-amber-400' : 'bg-coral'
</script>

<template>
  <div class="w-full bg-cream-dark rounded-full h-4 overflow-hidden">
    <div
      class="h-4 rounded-full transition-all duration-500 ease-out"
      :class="colorClass"
      :style="{ width: percentage + '%' }"
    ></div>
  </div>
</template>
