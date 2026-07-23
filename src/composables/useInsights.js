export function useInsights() {

  function computeInsights(transactions, categories, budgetSummary, balances) {
    const insights = []
    const now = new Date()
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    const prevDate = new Date(now.getFullYear(), now.getMonth() - 1, 1)
    const prevMonth = `${prevDate.getFullYear()}-${String(prevDate.getMonth() + 1).padStart(2, '0')}`

    const currentTxns = transactions.filter(t => t.date.startsWith(currentMonth))
    const prevTxns = transactions.filter(t => t.date.startsWith(prevMonth))

    const currentExpense = currentTxns.filter(t => t.type === 'expense')
    const prevExpense = prevTxns.filter(t => t.type === 'expense')

    const currentTotal = currentExpense.reduce((s, t) => s + t.amount, 0)
    const prevTotal = prevExpense.reduce((s, t) => s + t.amount, 0)

    if (prevTotal > 0) {
      const pctChange = ((currentTotal - prevTotal) / prevTotal) * 100
      if (Math.abs(pctChange) > 10) {
        insights.push({
          icon: pctChange > 0 ? '📈' : '📉',
          text: `You spent ${Math.abs(pctChange).toFixed(0)}% ${pctChange > 0 ? 'more' : 'less'} this month vs last month`,
          color: pctChange > 0 ? 'text-carrot-600' : 'text-kangkong-600',
        })
      }
    }

    const catSpend = {}
    for (const t of currentExpense) {
      catSpend[t.category] = (catSpend[t.category] || 0) + t.amount
    }

    const prevCatSpend = {}
    for (const t of prevExpense) {
      prevCatSpend[t.category] = (prevCatSpend[t.category] || 0) + t.amount
    }

    for (const [cat, spent] of Object.entries(catSpend)) {
      const prev = prevCatSpend[cat] || 0
      if (prev > 0 && spent > prev * 1.5) {
        const pct = ((spent - prev) / prev * 100).toFixed(0)
        insights.push({
          icon: '⚠️',
          text: `${cat} spending up ${pct}% vs last month`,
          color: 'text-carrot-600',
        })
      }
    }

    if (budgetSummary?.categories) {
      for (const cat of budgetSummary.categories) {
        if (cat.budget > 0 && cat.spent / cat.budget > 0.9) {
          insights.push({
            icon: '🔴',
            text: `${cat.name} at ${((cat.spent / cat.budget) * 100).toFixed(0)}% of budget`,
            color: 'text-tomato-600',
          })
        }
      }
    }

    const totalNetWorth = balances.reduce((s, b) => s + b.balance_display, 0)
    const milestones = [5000, 10000, 15000, 20000, 25000, 30000, 50000, 100000]
    for (const m of milestones) {
      if (totalNetWorth >= m && totalNetWorth < m * 1.05) {
        insights.push({
          icon: '🎉',
          text: `Net worth crossed $${m.toLocaleString()}!`,
          color: 'text-kangkong-600',
        })
        break
      }
    }

    const topCats = Object.entries(catSpend)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)

    if (topCats.length > 0 && currentTotal > 0) {
      const [topCat, topAmt] = topCats[0]
      const pct = ((topAmt / currentTotal) * 100).toFixed(0)
      insights.push({
        icon: '💡',
        text: `${topCat} is your biggest expense at ${pct}% of total spending`,
        color: 'text-mushroom-600',
      })
    }

    return insights.slice(0, 5)
  }

  return { computeInsights }
}
