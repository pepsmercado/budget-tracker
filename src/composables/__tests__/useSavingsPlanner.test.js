import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useSavingsPlanner } from '../useSavingsPlanner.js'

vi.mock('../../api.js', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('../useToast.js', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}))

import api from '../../api.js'

const plannerState = (overrides = {}) => ({
  planner: { id: 'p1', currency: 'PHP', linked_account_id: 'a1' },
  linked_account: { id: 'a1', name: 'Savings' },
  balance: 10000,
  unallocated: 2500,
  underfunded: false,
  reserves: [{ id: 'r1', name: 'Emergency', allocated: 3000, floor: 1000 }],
  goals: [{ id: 'g1', name: 'Japan', target: 5000, allocated: 2500 }],
  activity: [{ id: 'x1', type: 'Moved Funds', amount: 500, description: 'Moved 500.00 to Japan', created_at: '2026-08-01T10:00:00' }],
  savings_accounts: [{ id: 'a1', name: 'Savings' }],
  ...overrides,
})

describe('useSavingsPlanner', () => {
  let composable

  beforeEach(() => {
    vi.clearAllMocks()
    composable = useSavingsPlanner()
  })

  it('fetchPlanner loads state and exposes derived values', async () => {
    api.get.mockResolvedValue({ data: plannerState() })
    await composable.fetchPlanner('PHP')
    expect(api.get).toHaveBeenCalledWith('/savings-planner/PHP', { params: { limit: 50 } })
    expect(composable.linked.value).toBe(true)
    expect(composable.balance.value).toBe(10000)
    expect(composable.unallocated.value).toBe(2500)
    expect(composable.reserves.value).toHaveLength(1)
    expect(composable.goals.value).toHaveLength(1)
    expect(composable.activity.value).toHaveLength(1)
    expect(composable.loading.value).toBe(false)
  })

  it('fetchPlanner passes custom limit', async () => {
    api.get.mockResolvedValue({ data: plannerState() })
    await composable.fetchPlanner('PHP', 10)
    expect(api.get).toHaveBeenCalledWith('/savings-planner/PHP', { params: { limit: 10 } })
  })

  it('fetchPlanner handles unlinked state', async () => {
    api.get.mockResolvedValue({ data: plannerState({ planner: null, linked_account: null, balance: 0 }) })
    await composable.fetchPlanner('PHP')
    expect(composable.linked.value).toBe(false)
    expect(composable.savingsAccounts.value).toHaveLength(1)
  })

  it('linkPlanner posts account_id and updates state', async () => {
    const data = plannerState()
    api.post.mockResolvedValue({ data })
    await composable.linkPlanner('PHP', 'a1')
    expect(api.post).toHaveBeenCalledWith('/savings-planner/PHP/link', { account_id: 'a1' })
    expect(composable.linked.value).toBe(true)
  })

  it('createReserve posts payload', async () => {
    api.post.mockResolvedValue({ data: plannerState() })
    await composable.createReserve('PHP', { name: 'Tuition', allocated: 0, floor: 1000 })
    expect(api.post).toHaveBeenCalledWith('/savings-planner/PHP/reserves', { name: 'Tuition', allocated: 0, floor: 1000 })
  })

  it('updateReserve posts to reserve id', async () => {
    api.put.mockResolvedValue({ data: plannerState() })
    await composable.updateReserve('PHP', 'r1', { floor: 5000 })
    expect(api.put).toHaveBeenCalledWith('/savings-planner/PHP/reserves/r1', { floor: 5000 })
  })

  it('deleteReserve calls DELETE', async () => {
    api.delete.mockResolvedValue({ data: plannerState() })
    await composable.deleteReserve('PHP', 'r1')
    expect(api.delete).toHaveBeenCalledWith('/savings-planner/PHP/reserves/r1')
  })

  it('createGoal posts payload', async () => {
    api.post.mockResolvedValue({ data: plannerState() })
    await composable.createGoal('PHP', { name: 'Waterpark', target: 5000, allocated: 0 })
    expect(api.post).toHaveBeenCalledWith('/savings-planner/PHP/goals', { name: 'Waterpark', target: 5000, allocated: 0 })
  })

  it('updateGoal posts with position for reordering', async () => {
    api.put.mockResolvedValue({ data: plannerState() })
    await composable.updateGoal('PHP', 'g1', { position: 1 })
    expect(api.put).toHaveBeenCalledWith('/savings-planner/PHP/goals/g1', { position: 1 })
  })

  it('deleteGoal calls DELETE', async () => {
    api.delete.mockResolvedValue({ data: plannerState() })
    await composable.deleteGoal('PHP', 'g1')
    expect(api.delete).toHaveBeenCalledWith('/savings-planner/PHP/goals/g1')
  })

  it('convertGoal posts to convert endpoint', async () => {
    api.post.mockResolvedValue({ data: plannerState() })
    await composable.convertGoal('PHP', 'g1')
    expect(api.post).toHaveBeenCalledWith('/savings-planner/PHP/goals/g1/convert')
  })

  it('moveMoney posts move payload', async () => {
    api.post.mockResolvedValue({ data: plannerState() })
    await composable.moveMoney('PHP', { from_bucket: 'unallocated', to_bucket: 'g1', amount: 500 })
    expect(api.post).toHaveBeenCalledWith('/savings-planner/PHP/move', { from_bucket: 'unallocated', to_bucket: 'g1', amount: 500 })
  })

  it('allocateMoney posts allocations array', async () => {
    api.post.mockResolvedValue({ data: plannerState() })
    await composable.allocateMoney('PHP', [{ to_bucket: 'g1', amount: 1500 }])
    expect(api.post).toHaveBeenCalledWith('/savings-planner/PHP/allocate', {
      allocations: [{ to_bucket: 'g1', amount: 1500 }],
    })
  })

  it('underfunded reflects state flag', async () => {
    api.get.mockResolvedValue({ data: plannerState({ underfunded: true, unallocated: -500 }) })
    await composable.fetchPlanner('PHP')
    expect(composable.underfunded.value).toBe(true)
  })
})
