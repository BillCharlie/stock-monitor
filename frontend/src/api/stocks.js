// API base: use VITE_API_BASE_URL env var when deployed to GitHub Pages,
// otherwise fall back to same-origin /api (local FastAPI backend).
const BASE = import.meta.env.VITE_API_BASE_URL
  ? import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '') + '/api'
  : '/api'

import { obfuscate, deobfuscate, hashKey } from './crypto.js'

// Keys stored obfuscated in localStorage; only SHA-256 hash is ever sent over the wire.
export const keys = {
  getReport: () => deobfuscate(localStorage.getItem('sm_report_key') || ''),
  getStock:  () => deobfuscate(localStorage.getItem('sm_stock_key')  || ''),
  setReport: (v) => localStorage.setItem('sm_report_key', obfuscate(v)),
  setStock:  (v) => localStorage.setItem('sm_stock_key',  obfuscate(v)),
  hasReport: () => !!localStorage.getItem('sm_report_key'),
  hasStock:  () => !!localStorage.getItem('sm_stock_key'),
}

async function reportHeaders() {
  const hash = await hashKey(keys.getReport())
  return { 'Content-Type': 'application/json', ...(hash ? { 'X-API-Secret': hash } : {}) }
}

async function stockHeaders() {
  const hash = await hashKey(keys.getStock())
  return { 'Content-Type': 'application/json', ...(hash ? { 'X-API-Secret': hash } : {}) }
}

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

  generateReport: async () => request('/analysis/generate', { method: 'POST', headers: await reportHeaders() }),

  triggerGptReport: async () => request('/analysis/gpt-report', { method: 'POST', headers: await reportHeaders() }),

  downloadPdfUrl: () => `${BASE}/analysis/download-report`,

  // Custom stocks
  getCustomStocks: () => request('/custom-stocks'),

  addCustomStock: async (symbol, name) =>
    request('/custom-stocks', {
      method: 'POST',
      headers: await stockHeaders(),
      body: JSON.stringify({ symbol, name }),
    }),

  deleteCustomStock: async (symbol) =>
    request(`/custom-stocks/${encodeURIComponent(symbol)}`, {
      method: 'DELETE',
      headers: await stockHeaders(),
    }),
}
