<script setup>
const props = defineProps({ spent: Number, budget: Number })

const percentage = props.budget > 0 ? Math.min((props.spent / props.budget) * 100, 100) : 0
const colorClass = percentage < 60 ? 'bg-kangkong-500' : percentage < 85 ? 'bg-mango-500' : 'bg-tomato-500'
</script>

<template>
  <div class="w-full bg-mushroom-100 rounded-full h-2">
    <div
      class="h-2 rounded-full transition-all duration-500 ease-out"
      :class="colorClass"
      :style="{ width: percentage + '%' }"
    ></div>
  </div>
</template>
