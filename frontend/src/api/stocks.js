import { obfuscate, deobfuscate, hashKey } from './crypto.js'

// BASE is initialized at runtime from api-config.json.
// If the configured public backend is gone, requests fall back to same-origin
// /api and then a local backend so the app still works during deployment issues.
let BASE = '/api'
let BASES = ['/api']

function apiBaseFromOrigin(origin) {
  if (!origin) return ''
  return origin.replace(/\/$/, '') + '/api'
}

function uniqueBases(values) {
  return [...new Set(values.filter(Boolean))]
}

function localBackendBase() {
  if (typeof window === 'undefined') return ''
  const protocol = window.location.protocol === 'https:' ? 'http:' : window.location.protocol
  return `${protocol}//127.0.0.1:8765/api`
}

const _configReady = (async () => {
  const bases = []
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}api-config.json`)
    if (res.ok) {
      const cfg = await res.json()
      if (cfg.apiBaseUrl) {
        bases.push(apiBaseFromOrigin(cfg.apiBaseUrl))
      }
    }
  } catch {
    // local mode: no config file
  }
  bases.push('/api')
  bases.push(localBackendBase())
  BASES = uniqueBases(bases)
  BASE = BASES[0] || '/api'
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
  let lastError = null

  for (const base of BASES) {
    try {
      const res = await fetch(base + path, options)
      if (res.ok) {
        BASE = base
        return res.json()
      }

      const err = await res.json().catch(() => ({ detail: res.statusText }))
      const message = err.detail || err.message || `HTTP ${res.status}`
      const canFallback =
        res.status >= 500 ||
        message === 'Application not found' ||
        (res.status === 404 && base === '/api')

      lastError = new Error(message)
      if (!canFallback) {
        lastError.noFallback = true
        throw lastError
      }
    } catch (err) {
      if (err?.noFallback) {
        throw err
      }
      lastError = err
    }
  }

  throw lastError || new Error('Unable to connect to API')
}

export const api = {
  getWatchlist: () => request('/watchlist'),

  getKline: (symbol, interval = '1d', refresh = false) =>
    request(`/stocks/${encodeURIComponent(symbol)}/kline?interval=${interval}${refresh ? '&refresh=true' : ''}`),

  getQuote: (symbol) => request(`/stocks/${encodeURIComponent(symbol)}/quote`),

  getInvestors: (symbol, refresh = false) =>
    request(`/stocks/${encodeURIComponent(symbol)}/investors${refresh ? '?refresh=true' : ''}`),

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

  getUserWatchlist: () => request('/user-watchlist'),

  saveUserWatchlist: async (watchlist) => request('/user-watchlist', {
    method: 'PUT',
    headers: await stockHeaders(),
    body: JSON.stringify({ watchlist }),
  }),

  // Portfolios (資產管理)
  getPortfolios: () => request('/portfolios'),

  savePortfolios: async (persons) => request('/portfolios', {
    method: 'PUT',
    headers: await stockHeaders(),
    body: JSON.stringify({ persons }),
  }),

  getPositionAnalysis: (symbol, entry, entryDate = '') => {
    const params = new URLSearchParams({ symbol, entry: String(entry) })
    if (entryDate) params.set('entry_date', entryDate)
    return request(`/portfolio/position-analysis?${params.toString()}`)
  },

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

  getTrumpNews: (force = false) =>
    request(`/trump-news${force ? '?force=true' : ''}`),

  getEtfHoldings: (symbol, refresh = false) =>
    request(`/etf-holdings/${encodeURIComponent(symbol)}${refresh ? '?refresh=true' : ''}`),

  getAllEtfHoldings: (refresh = false) =>
    request(`/etf-holdings${refresh ? '?refresh=true' : ''}`),

  getEtfSectorSummary: (refresh = false, holdingsRefresh = refresh) => {
    const params = new URLSearchParams()
    if (refresh) params.set('refresh', 'true')
    if (holdingsRefresh) params.set('holdings_refresh', 'true')
    const qs = params.toString()
    return request(`/etf-holdings/sector-summary${qs ? '?' + qs : ''}`)
  },

  getHealth: () => request('/health'),

  refreshAll: async () => request('/data/refresh-all', {
    method: 'POST',
    headers: await reportHeaders(),
  }),
}
