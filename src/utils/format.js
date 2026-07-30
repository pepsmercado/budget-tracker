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

export const CHART_COLORS = ['#c2652a', '#e6a817', '#d1c893', '#e07c2e', '#666034', '#c9b68c', '#a5a58d', '#b8845c', '#e76f51', '#8a7f35']
