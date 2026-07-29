<script setup>
import { icons } from './icons.js'
defineProps({ name: String })
</script>
<template>
  <span v-html="icons[name]" />
</template>
