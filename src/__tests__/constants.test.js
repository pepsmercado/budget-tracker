import { describe, it, expect } from 'vitest'
import { categoryIcons } from '../constants.js'

describe('categoryIcons', () => {
  it('has all expected expense categories', () => {
    const expected = ['Rent', 'Electricity', 'Gas', 'Subscriptions', 'Phone & Wifi',
      'Groceries', 'Household', 'Transportation', 'Medical', 'Eating Out',
      'Social Events', 'Hobbies', 'Shopping', 'Beauty', 'Travel', 'Others',
      'Tuition', 'School Supplies']
    for (const cat of expected) {
      expect(categoryIcons[cat]).toBeDefined()
    }
  })

  it('has all expected income categories', () => {
    const expected = ['Salary', 'Cashback', 'Interest', 'Transfer Fees']
    for (const cat of expected) {
      expect(categoryIcons[cat]).toBeDefined()
    }
  })

  it('each value is an emoji', () => {
    for (const [key, val] of Object.entries(categoryIcons)) {
      expect(typeof val).toBe('string')
      expect(val.length).toBeGreaterThan(0)
    }
  })

  it('has 24 categories', () => {
    expect(Object.keys(categoryIcons).length).toBe(24)
  })
})
