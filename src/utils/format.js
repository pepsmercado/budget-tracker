export function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
}

export function formatCurrency(value, symbol) {
  return `${symbol}${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function formatMonthYear(year, month) {
  const d = new Date(year, parseInt(month) - 1)
  return d.toLocaleString('en-US', { month: 'long', year: 'numeric' })
}

export function shortMonth(month) {
  const d = new Date(2000, parseInt(month) - 1)
  return d.toLocaleString('en-US', { month: 'short' })
}

export const CHART_COLORS = ['#17ad49', '#da2f38', '#8952f6', '#f59e0b', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1', '#14b8a6']
