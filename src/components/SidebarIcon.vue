<script setup>
import { icons } from './icons.js'
defineProps({ name: String })
</script>
<template>
  <span class="w-5 h-5 flex items-center justify-center" v-html="icons[name]" />
</template>
