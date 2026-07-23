<script setup>
const props = defineProps({ name: String, group: String })

const groupColors = {
  Fixed: 'bg-coral/15 text-coral-dark',
  Essential: 'bg-sage/15 text-sage-dark',
  Lifestyle: 'bg-purple-100 text-purple-700',
  Sinking: 'bg-blue-100 text-blue-700',
  School: 'bg-amber-100 text-amber-700',
  Income: 'bg-emerald-100 text-emerald-700',
  Misc: 'bg-gray-100 text-gray-600',
}

const colorClass = groupColors[props.group] || 'bg-gray-100 text-gray-600'
</script>

<template>
  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold" :class="colorClass">
    {{ name }}
  </span>
</template>
