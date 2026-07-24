import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ToastContainer from '../ToastContainer.vue'
import { useToast } from '../../composables/useToast.js'

describe('ToastContainer', () => {
  let toast

  beforeEach(() => {
    vi.useFakeTimers()
    toast = useToast()
    toast.toasts.value = []
  })

  it('renders toasts from useToast', () => {
    toast.success('Test message')
    const wrapper = mount(ToastContainer)
    expect(wrapper.text()).toContain('Test message')
  })

  it('renders error toast with correct class', () => {
    toast.error('Error!')
    const wrapper = mount(ToastContainer)
    const toastEl = wrapper.find('[class*="bg-tomato"]')
    expect(toastEl.exists()).toBe(true)
    expect(toastEl.text()).toContain('Error!')
  })

  it('dismiss button removes toast', async () => {
    toast.success('Dismissible')
    const wrapper = mount(ToastContainer)
    const dismissBtn = wrapper.find('button')
    await dismissBtn.trigger('click')
    expect(toast.toasts.value.length).toBe(0)
  })

  it('renders nothing when no toasts', () => {
    const wrapper = mount(ToastContainer)
    expect(wrapper.findAll('button').length).toBe(0)
  })
})
