import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useTransactions } from '../useTransactions.js'

vi.mock('../../api.js', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import api from '../../api.js'

describe('useTransactions', () => {
  let composable

  beforeEach(() => {
    vi.clearAllMocks()
    composable = useTransactions()
  })

  it('fetchTransactions loads transactions', async () => {
    const mockTxns = [{ id: '1', amount: 500 }]
    api.get.mockResolvedValue({ data: mockTxns })
    await composable.fetchTransactions()
    expect(composable.transactions.value).toEqual(mockTxns)
  })

  it('fetchTransactions passes filters as params', async () => {
    api.get.mockResolvedValue({ data: [] })
    await composable.fetchTransactions({ type: 'income', currency: 'PHP' })
    expect(api.get).toHaveBeenCalledWith('/transactions', {
      params: { type: 'income', currency: 'PHP' },
    })
  })

  it('fetchTransactions omits empty filters', async () => {
    api.get.mockResolvedValue({ data: [] })
    await composable.fetchTransactions({ type: '', group: '' })
    expect(api.get).toHaveBeenCalledWith('/transactions', { params: {} })
  })

  it('createTransaction prepends to list', async () => {
    composable.transactions.value = [{ id: '1' }]
    const newTxn = { id: '2', amount: 100 }
    api.post.mockResolvedValue({ data: newTxn })
    const result = await composable.createTransaction(newTxn)
    expect(result).toEqual(newTxn)
    expect(composable.transactions.value[0]).toEqual(newTxn)
    expect(composable.transactions.value.length).toBe(2)
  })

  it('updateTransaction updates in list', async () => {
    composable.transactions.value = [{ id: '1', amount: 500 }]
    const updated = { id: '1', amount: 999 }
    api.put.mockResolvedValue({ data: updated })
    await composable.updateTransaction('1', updated)
    expect(composable.transactions.value[0].amount).toBe(999)
  })

  it('deleteTransaction removes from list', async () => {
    composable.transactions.value = [{ id: '1' }, { id: '2' }]
    api.delete.mockResolvedValue({})
    await composable.deleteTransaction('1')
    expect(composable.transactions.value.length).toBe(1)
    expect(composable.transactions.value[0].id).toBe('2')
  })

  it('loading is false after fetch completes', async () => {
    api.get.mockResolvedValue({ data: [] })
    await composable.fetchTransactions()
    expect(composable.loading.value).toBe(false)
  })
})
