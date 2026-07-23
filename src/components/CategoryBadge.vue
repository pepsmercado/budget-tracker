<script setup>
const props = defineProps({ name: String, group: String })

const groupColors = {
  Fixed: 'bg-tomato-50 text-tomato-700',
  Essential: 'bg-kangkong-50 text-kangkong-700',
  Lifestyle: 'bg-ubas-50 text-ubas-700',
  Sinking: 'bg-blueberry-50 text-blueberry-600',
  School: 'bg-mango-50 text-mango-700',
  Income: 'bg-kangkong-100 text-kangkong-800',
  Misc: 'bg-mushroom-100 text-mushroom-600',
}

const colorClass = groupColors[props.group] || 'bg-mushroom-100 text-mushroom-600'
</script>

<template>
  <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium" :class="colorClass">
    {{ name }}
  </span>
</template>
