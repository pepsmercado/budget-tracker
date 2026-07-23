<script setup>
import { computed } from 'vue'

const props = defineProps({
  spent: { type: Number, default: 0 },
  budget: { type: Number, default: 0 },
  greenThreshold: { type: Number, default: 0.7 },
  orangeThreshold: { type: Number, default: 0.9 },
})

const percentage = computed(() => props.budget > 0 ? Math.min((props.spent / props.budget) * 100, 100) : 0)
const ratio = computed(() => props.budget > 0 ? props.spent / props.budget : 0)
const colorClass = computed(() => {
  if (ratio.value < props.greenThreshold) return 'bg-kangkong-500'
  if (ratio.value < props.orangeThreshold) return 'bg-carrot-500'
  return 'bg-tomato-500'
})
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
