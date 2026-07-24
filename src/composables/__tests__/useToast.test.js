import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useToast } from '../useToast.js'

describe('useToast', () => {
  let toast

  beforeEach(() => {
    vi.useFakeTimers()
    toast = useToast()
    toast.toasts.value = []
    vi.restoreAllMocks()
  })

  it('adds a success toast', () => {
    const id = toast.success('It worked')
    expect(toast.toasts.value.length).toBe(1)
    expect(toast.toasts.value[0].message).toBe('It worked')
    expect(toast.toasts.value[0].type).toBe('success')
  })

  it('adds an error toast', () => {
    toast.error('Something broke')
    expect(toast.toasts.value[0].type).toBe('error')
    expect(toast.toasts.value[0].message).toBe('Something broke')
  })

  it('adds an info toast', () => {
    toast.info('FYI')
    expect(toast.toasts.value[0].type).toBe('info')
  })

  it('adds a warning toast', () => {
    toast.warning('Careful')
    expect(toast.toasts.value[0].type).toBe('warning')
  })

  it('dismisses a toast by id', () => {
    const id = toast.success('Test')
    expect(toast.toasts.value.length).toBe(1)
    toast.dismiss(id)
    expect(toast.toasts.value.length).toBe(0)
  })

  it('auto-dismisses after duration', () => {
    toast.success('Auto', 1000)
    expect(toast.toasts.value.length).toBe(1)
    vi.advanceTimersByTime(1000)
    expect(toast.toasts.value.length).toBe(0)
  })

  it('error has default 5000ms duration', () => {
    toast.error('Error')
    vi.advanceTimersByTime(4999)
    expect(toast.toasts.value.length).toBe(1)
    vi.advanceTimersByTime(1)
    expect(toast.toasts.value.length).toBe(0)
  })

  it('returns unique ids', () => {
    const id1 = toast.success('First')
    const id2 = toast.success('Second')
    expect(id1).not.toBe(id2)
  })

  it('dismiss is safe for nonexistent id', () => {
    toast.dismiss(999)
    expect(toast.toasts.value.length).toBe(0)
  })
})
