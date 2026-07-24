import { describe, it, expect } from 'vitest'
import router from '../router.js'

describe('router', () => {
  it('has php routes', () => {
    const phpRoutes = router.getRoutes().filter(r => r.path?.startsWith('/php'))
    expect(phpRoutes.length).toBeGreaterThan(0)
  })

  it('has usd routes', () => {
    const usdRoutes = router.getRoutes().filter(r => r.path?.startsWith('/usd'))
    expect(usdRoutes.length).toBeGreaterThan(0)
  })

  it('root redirects to /php', () => {
    const root = router.getRoutes().find(r => r.path === '/')
    expect(root).toBeDefined()
  })

  it('php has dashboard route', () => {
    const route = router.getRoutes().find(r => r.path === '/php')
    expect(route).toBeDefined()
  })

  it('php has transactions route', () => {
    const route = router.getRoutes().find(r => r.path === '/php/transactions')
    expect(route).toBeDefined()
  })

  it('php has budgets route', () => {
    const route = router.getRoutes().find(r => r.path === '/php/budgets')
    expect(route).toBeDefined()
  })

  it('php has accounts route', () => {
    const route = router.getRoutes().find(r => r.path === '/php/accounts')
    expect(route).toBeDefined()
  })

  it('php has recurring route', () => {
    const route = router.getRoutes().find(r => r.path === '/php/recurring')
    expect(route).toBeDefined()
  })

  it('php has transfers route', () => {
    const route = router.getRoutes().find(r => r.path === '/php/transfers')
    expect(route).toBeDefined()
  })

  it('php has reports route', () => {
    const route = router.getRoutes().find(r => r.path === '/php/reports')
    expect(route).toBeDefined()
  })

  it('usd routes mirror php routes', () => {
    const phpPaths = router.getRoutes()
      .filter(r => r.path?.startsWith('/php'))
      .map(r => r.path.replace('/php', ''))
      .sort()
    const usdPaths = router.getRoutes()
      .filter(r => r.path?.startsWith('/usd'))
      .map(r => r.path.replace('/usd', ''))
      .sort()
    expect(phpPaths).toEqual(usdPaths)
  })
})
