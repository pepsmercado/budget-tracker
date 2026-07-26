<script setup>
import { onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const { isVerified, isEnabled, error, loading, checkStatus, verify } = useAuth()

const pin = ref('')
const showPin = ref(false)

onMounted(checkStatus)

async function handleSubmit() {
  if (pin.value.length < 4) return
  await verify(pin.value)
  pin.value = ''
}

function handleInput(e) {
  pin.value = e.target.value.replace(/\D/g, '').slice(0, 6)
}
</script>

<template>
  <div v-if="!isEnabled || isVerified" class="contents">
    <slot />
  </div>
  <div v-else class="flex h-screen bg-[#f0eeea] dark:bg-[#0e1218] items-center justify-center p-5">
    <div class="w-full max-w-sm">
      <div class="card-elevated p-8 text-center">
        <div class="w-16 h-16 mx-auto mb-5 rounded-full bg-mushroom-100 dark:bg-mushroom-800 flex items-center justify-center">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-mushroom-600 dark:text-mushroom-400">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0110 0v4"/>
          </svg>
        </div>
        <h2 class="text-lg font-medium text-mushroom-950 dark:text-mushroom-50 mb-1">Enter Access Code</h2>
        <p class="text-xs text-mushroom-400 dark:text-mushroom-500 mb-6">Enter your PIN to access the budget tracker</p>

        <form @submit.prevent="handleSubmit" class="space-y-4">
          <div class="relative">
            <input
              :type="showPin ? 'text' : 'password'"
              :value="pin"
              @input="handleInput"
              inputmode="numeric"
              pattern="[0-9]*"
              maxlength="6"
              placeholder="••••"
              autofocus
              class="w-full text-center text-2xl tracking-[0.5em] py-3 px-4 bg-mushroom-50 dark:bg-mushroom-800 border border-mushroom-200 dark:border-mushroom-700 rounded-lg text-mushroom-950 dark:text-mushroom-50 placeholder:text-mushroom-300 dark:placeholder:text-mushroom-600 focus:outline-none focus:ring-2 focus:ring-kangkong-500/20 focus:border-kangkong-500"
            />
            <button
              type="button"
              @click="showPin = !showPin"
              class="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-mushroom-400 dark:text-mushroom-500 hover:text-mushroom-600 dark:hover:text-mushroom-300"
            >
              <svg v-if="!showPin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>

          <p v-if="error" class="text-xs text-tomato-600 dark:text-tomato-400">{{ error }}</p>

          <button
            type="submit"
            :disabled="pin.length < 4 || loading"
            class="w-full py-2.5 bg-kangkong-600 hover:bg-kangkong-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            {{ loading ? 'Verifying...' : 'Unlock' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
