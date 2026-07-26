<script setup>
defineProps({
  width: { type: String, default: '100%' },
  height: { type: String, default: '1rem' },
  rounded: { type: String, default: 'rounded' },
})
</script>

<template>
  <div
    class="bg-mushroom-100 dark:bg-[#262c40] animate-pulse"
    :class="rounded"
    :style="{ width, height }"
  />
</template>
