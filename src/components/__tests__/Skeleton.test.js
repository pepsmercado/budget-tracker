import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Skeleton from '../Skeleton.vue'

describe('Skeleton', () => {
  it('renders with default props', () => {
    const wrapper = mount(Skeleton)
    const el = wrapper.find('div')
    expect(el.classes()).toContain('animate-pulse')
    expect(el.attributes('style')).toContain('width: 100%')
    expect(el.attributes('style')).toContain('height: 1rem')
  })

  it('renders with custom width and height', () => {
    const wrapper = mount(Skeleton, { props: { width: '200px', height: '50px' } })
    const el = wrapper.find('div')
    expect(el.attributes('style')).toContain('width: 200px')
    expect(el.attributes('style')).toContain('height: 50px')
  })

  it('applies rounded class', () => {
    const wrapper = mount(Skeleton, { props: { rounded: 'rounded-lg' } })
    expect(wrapper.find('div').classes()).toContain('rounded-lg')
  })

  it('default rounded is rounded', () => {
    const wrapper = mount(Skeleton)
    expect(wrapper.find('div').classes()).toContain('rounded')
  })
})
