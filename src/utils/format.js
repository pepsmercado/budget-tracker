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

export const CHART_COLORS = ['#6366f1', '#10b981', '#fb7185', '#a855f7', '#0ea5e9', '#e6a817', '#e07c2e', '#8e8b9d', '#34d399', '#818cf8']
