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

export const CHART_COLORS = ['#4caf50', '#c2652a', '#d4a373', '#e6a817', '#e76f51', '#a5a58d', '#c9b68c', '#e07c2e', '#d97706', '#b8845c']
