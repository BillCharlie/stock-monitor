import { obfuscate, deobfuscate, hashKey } from './crypto.js'

// BASE is initialized at runtime from api-config.json (GitHub Pages) or falls back to /api (local).
// This avoids baking a dynamic tunnel URL into the JS bundle at build time.
let BASE = '/api'

const _configReady = (async () => {
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}api-config.json`)
    if (res.ok) {
      const cfg = await res.json()
      if (cfg.apiBaseUrl) {
        BASE = cfg.apiBaseUrl.replace(/\/$/, '') + '/api'
      }
    }
  } catch {
    // local mode: no config file, BASE stays '/api'
  }
})()

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
  await _configReady
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

  getInvestors: (symbol) => request(`/stocks/${encodeURIComponent(symbol)}/investors`),

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

  pingAuth: async (type) => request('/auth/ping', {
    method: 'POST',
    headers: await (type === 'report' ? reportHeaders() : stockHeaders()),
  }),

  getNews: (category = null, force = false) => {
    const params = new URLSearchParams()
    if (category) params.set('category', category)
    if (force) params.set('force', 'true')
    const qs = params.toString()
    return request(`/news${qs ? '?' + qs : ''}`)
  },
}
