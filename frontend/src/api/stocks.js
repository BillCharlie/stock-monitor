// API base: use VITE_API_BASE_URL env var when deployed to GitHub Pages,
// otherwise fall back to same-origin /api (local FastAPI backend).
const BASE = import.meta.env.VITE_API_BASE_URL
  ? import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '') + '/api'
  : '/api'

async function request(path, options) {
  const res = await fetch(BASE + path, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  getWatchlist: () => request('/watchlist'),

  getKline: (symbol, interval = '1d', refresh = false) =>
    request(`/stocks/${encodeURIComponent(symbol)}/kline?interval=${interval}${refresh ? '&refresh=true' : ''}`),

  getQuote: (symbol) => request(`/stocks/${encodeURIComponent(symbol)}/quote`),

  getAnalysis: (symbol, name = '') =>
    request(`/stocks/${encodeURIComponent(symbol)}/analysis?name=${encodeURIComponent(name)}`),

  getMarketOverview: () => request('/market/overview'),

  getDailyReport: () => request('/analysis/daily-report'),

  generateReport: () => request('/analysis/generate', { method: 'POST' }),

  triggerGptReport: () => request('/analysis/gpt-report', { method: 'POST' }),

  downloadPdfUrl: () => `${BASE}/analysis/download-report`,

  // Custom stocks
  getCustomStocks: () => request('/custom-stocks'),

  addCustomStock: (symbol, name) =>
    request('/custom-stocks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, name }),
    }),

  deleteCustomStock: (symbol) =>
    request(`/custom-stocks/${encodeURIComponent(symbol)}`, { method: 'DELETE' }),
}
