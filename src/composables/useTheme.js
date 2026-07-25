import { ref, computed, watchEffect } from 'vue'

const theme = ref(localStorage.getItem('theme') || 'system')

function getSystemTheme() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function getEffectiveTheme() {
  return theme.value === 'system' ? getSystemTheme() : theme.value
}

const isDark = computed(() => getEffectiveTheme() === 'dark')

function applyTheme() {
  document.documentElement.classList.toggle('dark', isDark.value)
}

applyTheme()

if (theme.value === 'system') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme)
}

watchEffect(() => {
  localStorage.setItem('theme', theme.value)
  applyTheme()
})

export function useTheme() {
  function setTheme(value) {
    theme.value = value
  }

  function toggleTheme() {
    const effective = getEffectiveTheme()
    theme.value = effective === 'dark' ? 'light' : 'dark'
  }

  return { theme, isDark, setTheme, toggleTheme }
}
