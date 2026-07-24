import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useTransfers } from '../useTransfers.js'

vi.mock('../../api.js', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import api from '../../api.js'

describe('useTransfers', () => {
  let composable

  beforeEach(() => {
    vi.clearAllMocks()
    composable = useTransfers()
  })

  it('fetchTransfers loads transfers', async () => {
    const mockTransfers = [{ id: '1', amount: 5000 }]
    api.get.mockResolvedValue({ data: mockTransfers })
    await composable.fetchTransfers('PHP')
    expect(composable.transfers.value).toEqual(mockTransfers)
    expect(api.get).toHaveBeenCalledWith('/transfers', { params: { currency: 'PHP' } })
  })

  it('fetchTransfers omits currency if not provided', async () => {
    api.get.mockResolvedValue({ data: [] })
    await composable.fetchTransfers()
    expect(api.get).toHaveBeenCalledWith('/transfers', { params: {} })
  })

  it('createTransfer returns data', async () => {
    const newTransfer = { id: '1', amount: 1000 }
    api.post.mockResolvedValue({ data: newTransfer })
    const result = await composable.createTransfer({ amount: 1000 })
    expect(result).toEqual(newTransfer)
  })

  it('deleteTransfer calls API', async () => {
    api.delete.mockResolvedValue({})
    await composable.deleteTransfer('1')
    expect(api.delete).toHaveBeenCalledWith('/transfers/1')
  })

  it('loading is false after fetch', async () => {
    api.get.mockResolvedValue({ data: [] })
    await composable.fetchTransfers()
    expect(composable.loading.value).toBe(false)
  })
})
