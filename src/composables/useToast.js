import { ref } from 'vue'

const toasts = ref([])
let nextId = 0

export function useToast() {
  function addToast(message, type = 'info', duration = 3500) {
    const id = nextId++
    toasts.value.push({ id, message, type })
    if (duration > 0) {
      setTimeout(() => dismiss(id), duration)
    }
    return id
  }

  function success(message, duration) { return addToast(message, 'success', duration) }
  function error(message, duration) { return addToast(message, 'error', duration || 5000) }
  function info(message, duration) { return addToast(message, 'info', duration) }
  function warning(message, duration) { return addToast(message, 'warning', duration) }

  function dismiss(id) {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  return { toasts, success, error, info, warning, dismiss }
}
