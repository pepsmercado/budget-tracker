import { ref, computed, watchEffect } from 'vue'

const isServer = typeof localStorage === 'undefined'

const theme = ref(isServer ? 'system' : localStorage.getItem('theme') || 'system')

function getSystemTheme() {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function getEffectiveTheme() {
  return theme.value === 'system' ? getSystemTheme() : theme.value
}

const isDark = computed(() => getEffectiveTheme() === 'dark')

function applyTheme() {
  if (typeof document === 'undefined') return
  document.documentElement.classList.toggle('dark', isDark.value)
}

applyTheme()

if (!isServer && typeof window !== 'undefined' && window.matchMedia && theme.value === 'system') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme)
}

watchEffect(() => {
  if (!isServer) {
    localStorage.setItem('theme', theme.value)
  }
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
