import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BudgetProgressBar from '../BudgetProgressBar.vue'

describe('BudgetProgressBar', () => {
  it('renders with default props', () => {
    const wrapper = mount(BudgetProgressBar)
    const bar = wrapper.find('[class*="rounded-full"]')
    expect(bar.exists()).toBe(true)
  })

  it('calculates percentage correctly', () => {
    const wrapper = mount(BudgetProgressBar, { props: { spent: 50, budget: 100 } })
    const bar = wrapper.findAll('[class*="rounded-full"]')[1]
    expect(bar.attributes('style')).toContain('width: 50%')
  })

  it('caps at 100%', () => {
    const wrapper = mount(BudgetProgressBar, { props: { spent: 200, budget: 100 } })
    const bar = wrapper.findAll('[class*="rounded-full"]')[1]
    expect(bar.attributes('style')).toContain('width: 100%')
  })

  it('green when under green threshold', () => {
    const wrapper = mount(BudgetProgressBar, { props: { spent: 50, budget: 100 } })
    const bar = wrapper.findAll('[class*="rounded-full"]')[1]
    expect(bar.classes()).toContain('bg-kangkong-500')
  })

  it('orange between thresholds', () => {
    const wrapper = mount(BudgetProgressBar, { props: { spent: 85, budget: 100 } })
    const bar = wrapper.findAll('[class*="rounded-full"]')[1]
    expect(bar.classes()).toContain('bg-carrot-500')
  })

  it('red above orange threshold', () => {
    const wrapper = mount(BudgetProgressBar, { props: { spent: 95, budget: 100 } })
    const bar = wrapper.findAll('[class*="rounded-full"]')[1]
    expect(bar.classes()).toContain('bg-tomato-500')
  })

  it('invert: green when high', () => {
    const wrapper = mount(BudgetProgressBar, { props: { spent: 95, budget: 100, invert: true } })
    const bar = wrapper.findAll('[class*="rounded-full"]')[1]
    expect(bar.classes()).toContain('bg-kangkong-500')
  })

  it('invert: red when low', () => {
    const wrapper = mount(BudgetProgressBar, { props: { spent: 10, budget: 100, invert: true } })
    const bar = wrapper.findAll('[class*="rounded-full"]')[1]
    expect(bar.classes()).toContain('bg-tomato-500')
  })

  it('zero budget shows 0%', () => {
    const wrapper = mount(BudgetProgressBar, { props: { spent: 0, budget: 0 } })
    const bar = wrapper.findAll('[class*="rounded-full"]')[1]
    expect(bar.attributes('style')).toContain('width: 0%')
  })
})
