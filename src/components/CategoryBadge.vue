<script setup>
const props = defineProps({ name: String, group: String })

const groupColors = {
  Fixed: 'bg-tomato-50 dark:bg-tomato-500/15 text-tomato-700 dark:text-tomato-400',
  Essential: 'bg-kangkong-50 dark:bg-kangkong-500/15 text-kangkong-700 dark:text-kangkong-400',
  Lifestyle: 'bg-carrot-50 dark:bg-carrot-500/15 text-carrot-700 dark:text-carrot-400',
  Sinking: 'bg-tomato-50 dark:bg-tomato-500/15 text-tomato-700 dark:text-tomato-400',
  School: 'bg-mango-50 dark:bg-mango-500/15 text-mango-700 dark:text-mango-400',
  Income: 'bg-kangkong-100 dark:bg-kangkong-500/15 text-kangkong-800 dark:text-kangkong-300',
  Misc: 'bg-mushroom-100 dark:bg-mushroom-700 text-mushroom-600 dark:text-mushroom-300',
}

const colorClass = groupColors[props.group] || 'bg-mushroom-100 dark:bg-mushroom-700 text-mushroom-600 dark:text-mushroom-300'
</script>

<template>
  <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium" :class="colorClass">
    {{ name }}
  </span>
</template>
