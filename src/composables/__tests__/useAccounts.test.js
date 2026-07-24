import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAccounts } from '../useAccounts.js'

vi.mock('../../api.js', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import api from '../../api.js'

describe('useAccounts', () => {
  let composable

  beforeEach(() => {
    vi.clearAllMocks()
    composable = useAccounts()
  })

  it('fetchAccounts loads accounts', async () => {
    const mockAccounts = [{ id: '1', name: 'Savings', currency: 'PHP' }]
    api.get.mockResolvedValue({ data: mockAccounts })
    await composable.fetchAccounts()
    expect(composable.accounts.value).toEqual(mockAccounts)
    expect(composable.loading.value).toBe(false)
  })

  it('fetchAccounts sets loading true during fetch', async () => {
    api.get.mockResolvedValue({ data: [] })
    const promise = composable.fetchAccounts()
    expect(composable.loading.value).toBe(true)
    await promise
    expect(composable.loading.value).toBe(false)
  })

  it('createAccount adds to list', async () => {
    const newAcc = { id: '2', name: 'New Account' }
    api.post.mockResolvedValue({ data: newAcc })
    const result = await composable.createAccount({ name: 'New Account' })
    expect(result).toEqual(newAcc)
    expect(composable.accounts.value).toContainEqual(newAcc)
  })

  it('updateAccount updates in list', async () => {
    composable.accounts.value = [{ id: '1', name: 'Old' }]
    const updated = { id: '1', name: 'New' }
    api.put.mockResolvedValue({ data: updated })
    await composable.updateAccount('1', { name: 'New' })
    expect(composable.accounts.value[0].name).toBe('New')
  })

  it('deleteAccount removes from list', async () => {
    composable.accounts.value = [{ id: '1', name: 'To Delete' }]
    api.delete.mockResolvedValue({})
    await composable.deleteAccount('1')
    expect(composable.accounts.value.length).toBe(0)
  })

  it('updateAccountGoal updates goal', async () => {
    composable.accounts.value = [{ id: '1', goal_amount: 0 }]
    const updated = { id: '1', goal_amount: 50000 }
    api.put.mockResolvedValue({ data: updated })
    await composable.updateAccountGoal('1', 50000)
    expect(composable.accounts.value[0].goal_amount).toBe(50000)
  })
})
