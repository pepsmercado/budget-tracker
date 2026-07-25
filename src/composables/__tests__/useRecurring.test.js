import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useRecurring } from '../useRecurring.js'

vi.mock('../../api.js', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import api from '../../api.js'

describe('useRecurring', () => {
  let composable

  beforeEach(() => {
    vi.clearAllMocks()
    composable = useRecurring()
  })

  it('fetchRules loads rules', async () => {
    const mockRules = [{ id: '1', name: 'Rent' }]
    api.get.mockResolvedValue({ data: mockRules })
    await composable.fetchRules('USD')
    expect(composable.rules.value).toEqual(mockRules)
    expect(api.get).toHaveBeenCalledWith('/recurring', { params: { currency: 'USD' } })
  })

  it('fetchRules omits currency if not provided', async () => {
    api.get.mockResolvedValue({ data: [] })
    await composable.fetchRules()
    expect(api.get).toHaveBeenCalledWith('/recurring', { params: {} })
  })

  it('createRule re-fetches list', async () => {
    const newRule = { id: '3', name: 'Internet' }
    api.post.mockResolvedValue({ data: newRule })
    api.get.mockResolvedValue({ data: [newRule] })
    const result = await composable.createRule({ name: 'Internet' })
    expect(result).toEqual(newRule)
    expect(api.get).toHaveBeenCalled()
    expect(composable.rules.value).toContainEqual(newRule)
  })

  it('updateRule re-fetches list', async () => {
    const updated = { id: '1', name: 'New' }
    api.put.mockResolvedValue({ data: updated })
    api.get.mockResolvedValue({ data: [updated] })
    await composable.updateRule('1', { name: 'New' })
    expect(api.get).toHaveBeenCalled()
    expect(composable.rules.value[0].name).toBe('New')
  })

  it('deleteRule re-fetches list', async () => {
    api.delete.mockResolvedValue({})
    api.get.mockResolvedValue({ data: [{ id: '2' }] })
    await composable.deleteRule('1')
    expect(api.get).toHaveBeenCalled()
    expect(composable.rules.value.length).toBe(1)
  })

  it('toggleRule re-fetches list', async () => {
    const toggled = { id: '1', active: false }
    api.put.mockResolvedValue({ data: toggled })
    api.get.mockResolvedValue({ data: [toggled] })
    await composable.toggleRule('1', false)
    expect(api.get).toHaveBeenCalled()
    expect(composable.rules.value[0].active).toBe(false)
  })

  it('runNow sets runResult and refreshes rules', async () => {
    const result = { generated: 2, rules: [{ id: '1' }, { id: '2' }] }
    api.post.mockResolvedValue({ data: result })
    const returned = await composable.runNow('USD')
    expect(returned).toEqual(result)
    expect(composable.runResult.value).toEqual(result)
    expect(composable.rules.value).toEqual(result.rules)
  })

  it('loading is toggled during runNow', async () => {
    api.post.mockResolvedValue({ data: { generated: 0, rules: [] } })
    const promise = composable.runNow()
    expect(composable.loading.value).toBe(true)
    await promise
    expect(composable.loading.value).toBe(false)
  })
})
