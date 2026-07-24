import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CategoryBadge from '../CategoryBadge.vue'

describe('CategoryBadge', () => {
  it('renders name', () => {
    const wrapper = mount(CategoryBadge, { props: { name: 'Groceries', group: 'Essential' } })
    expect(wrapper.text()).toContain('Groceries')
  })

  it('applies correct group color', () => {
    const wrapper = mount(CategoryBadge, { props: { name: 'Rent', group: 'Fixed' } })
    const span = wrapper.find('span')
    expect(span.classes()).toContain('bg-tomato-50')
    expect(span.classes()).toContain('text-tomato-700')
  })

  it('Essential group uses kangkong color', () => {
    const wrapper = mount(CategoryBadge, { props: { name: 'Food', group: 'Essential' } })
    expect(wrapper.find('span').classes()).toContain('bg-kangkong-50')
  })

  it('Income group uses kangkong-100', () => {
    const wrapper = mount(CategoryBadge, { props: { name: 'Salary', group: 'Income' } })
    expect(wrapper.find('span').classes()).toContain('bg-kangkong-100')
  })

  it('unknown group falls back to mushroom', () => {
    const wrapper = mount(CategoryBadge, { props: { name: 'X', group: 'Unknown' } })
    expect(wrapper.find('span').classes()).toContain('bg-mushroom-100')
  })
})
