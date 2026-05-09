import { useEffect, useState, useCallback } from 'react'
import { api, keys } from '../api/stocks.js'
import WatchlistEditor from './WatchlistEditor.jsx'

// ── Depth-based style config ───────────────────────────────────────────────────
const DEPTH_STYLES = [
  // depth 0 — 台灣 / 美國
  'bg-[#0F1A2A] text-blue-300 font-bold text-[11px] uppercase tracking-wide border-b border-[#1A2A3A]',
  // depth 1 — 半導體 / 資源
  'bg-[#111B11] text-green-300 font-semibold text-[11px] border-b border-[#1A2A1A]',
  // depth 2 — CPU/GPU產業 / 記憶體產業 etc
  'bg-[#141414] text-yellow-200 font-medium text-[10px] border-b border-[#222]',
  // depth 3 — IC設計 / IC代工 / DRAM產業 etc
  'bg-[#0D0D0D] text-[#9CDCFE] text-[10px] border-b border-[#1A1A1A]',
  // depth 4+ — extra nesting fallback
  'bg-[#0A0A0A] text-gray-500 text-[10px] border-b border-[#181818]',
]

// ── Individual stock row ───────────────────────────────────────────────────────
function StockRow({ stock, isSelected, onClick, onDelete, depth }) {
  const [quote, setQuote] = useState(null)
  const indent = Math.min(depth, 5) * 10 + 8

  useEffect(() => {
    let cancelled = false
    api.getQuote(stock.symbol).then(q => { if (!cancelled) setQuote(q) }).catch(() => {})
    return () => { cancelled = true }
  }, [stock.symbol])

  const isUp = quote?.change_pct >= 0
  const priceColor = quote ? (isUp ? 'text-[#EF5350]' : 'text-[#26A69A]') : 'text-gray-600'

  return (
    <div
      className={`flex items-center justify-between py-1 pr-2 cursor-pointer hover:bg-[#1A1A1A] transition-colors ${
        isSelected ? 'bg-[#1A2A3A] border-l-2 border-blue-500' : 'border-l-2 border-transparent'
      }`}
      style={{ paddingLeft: indent }}
      onClick={onClick}
    >
      <div className="flex flex-col min-w-0 flex-1">
        <span className="text-[11px] text-gray-200 truncate">{stock.name}</span>
        <span className="text-[9px] text-gray-600">{stock.symbol}</span>
      </div>
      <div className={`flex flex-col items-end flex-shrink-0 ml-1 ${priceColor}`}>
        {quote?.price != null ? (
          <>
            <span className="text-[10px] font-mono">{quote.price.toLocaleString()}</span>
            {quote.change_pct != null && (
              <span className="text-[9px] font-mono">{quote.change_pct >= 0 ? '+' : ''}{quote.change_pct.toFixed(2)}%</span>
            )}
          </>
        ) : (
          <span className="text-[9px]">─</span>
        )}
      </div>
      {onDelete && (
        <button
          onClick={e => { e.stopPropagation(); onDelete(stock.symbol) }}
          className="ml-1 text-gray-700 hover:text-red-400 text-[10px] flex-shrink-0"
          title="移除"
        >✕</button>
      )}
    </div>
  )
}

// ── Recursive tree node ────────────────────────────────────────────────────────
function TreeNode({ name, node, depth, onSelect, selectedSymbol, onDelete, isCustom }) {
  const [collapsed, setCollapsed] = useState(depth >= 2)
  const styleIdx = Math.min(depth, DEPTH_STYLES.length - 1)
  const indent = depth * 8

  // ── Leaf: array of stocks ──────────────────────────────────────────────────
  if (Array.isArray(node)) {
    if (node.length === 0) return null
    return (
      <div>
        <button
          onClick={() => setCollapsed(c => !c)}
          className={`w-full flex items-center justify-between px-2 py-1.5 hover:brightness-125 transition-all ${DEPTH_STYLES[styleIdx]}`}
          style={{ paddingLeft: 8 + indent }}
        >
          <span className="truncate">{name}</span>
          <span className="text-[9px] opacity-50 flex-shrink-0 ml-1">
            {collapsed ? `▶ ${node.length}` : '▼'}
          </span>
        </button>
        {!collapsed && (
          <div>
            {node.map(stock => (
              <StockRow
                key={stock.symbol}
                stock={stock}
                depth={depth + 1}
                isSelected={selectedSymbol === stock.symbol}
                onClick={() => onSelect(stock.symbol, stock.name)}
                onDelete={isCustom ? onDelete : null}
              />
            ))}
          </div>
        )}
      </div>
    )
  }

  // ── Branch: dict of sub-nodes ──────────────────────────────────────────────
  return (
    <div>
      <button
        onClick={() => setCollapsed(c => !c)}
        className={`w-full flex items-center justify-between px-2 py-1.5 hover:brightness-125 transition-all ${DEPTH_STYLES[styleIdx]}`}
        style={{ paddingLeft: 8 + indent }}
      >
        <span className="truncate">{name}</span>
        <span className="text-[9px] opacity-50 flex-shrink-0 ml-1">{collapsed ? '▶' : '▼'}</span>
      </button>
      {!collapsed && (
        <div>
          {Object.entries(node).map(([key, val]) => (
            <TreeNode
              key={key}
              name={key}
              node={val}
              depth={depth + 1}
              onSelect={onSelect}
              selectedSymbol={selectedSymbol}
              onDelete={onDelete}
              isCustom={isCustom}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Add stock modal ────────────────────────────────────────────────────────────
function AddStockModal({ onClose, onAdd }) {
  const [symbol, setSymbol] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    const sym = symbol.trim().toUpperCase()
    if (!sym) { setError('請輸入股票代號'); return }
    setLoading(true)
    setError('')
    try {
      await api.addCustomStock(sym, name.trim() || sym)
      onAdd()
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-5 w-72 shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="text-sm font-semibold text-white mb-4">新增自訂股票</div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-[10px] text-gray-400 block mb-1">股票代號 <span className="text-red-400">*</span></label>
            <input
              autoFocus
              value={symbol}
              onChange={e => setSymbol(e.target.value)}
              placeholder="例：2330.TW 或 NVDA"
              className="w-full bg-[#0D0D0D] border border-[#2A2A2A] rounded px-2 py-1.5 text-xs text-white placeholder-gray-600 outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="text-[10px] text-gray-400 block mb-1">顯示名稱（選填）</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="例：台積電"
              className="w-full bg-[#0D0D0D] border border-[#2A2A2A] rounded px-2 py-1.5 text-xs text-white placeholder-gray-600 outline-none focus:border-blue-500"
            />
          </div>
          {error && <div className="text-red-400 text-[10px]">{error}</div>}
          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-blue-700 hover:bg-blue-600 text-white rounded py-1.5 text-xs disabled:opacity-50"
            >
              {loading ? '新增中...' : '新增'}
            </button>
            <button type="button" onClick={onClose} className="flex-1 bg-[#2A2A2A] hover:bg-[#3A3A3A] text-gray-300 rounded py-1.5 text-xs">
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Main WatchlistPanel ────────────────────────────────────────────────────────
export default function WatchlistPanel({ onSelect, selectedSymbol, onNeedKey }) {
  const [categories, setCategories] = useState({})
  const [search, setSearch] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [showEditor, setShowEditor] = useState(false)

  const loadWatchlist = useCallback(() => {
    api.getWatchlist().then(data => setCategories(data.categories || {})).catch(() => {})
  }, [])

  useEffect(() => { loadWatchlist() }, [loadWatchlist])

  const handleDeleteCustom = async (symbol) => {
    if (!keys.hasStock()) { onNeedKey?.(); return }
    try {
      await api.deleteCustomStock(symbol)
      loadWatchlist()
    } catch (e) {
      alert('刪除失敗：' + e.message)
    }
  }

  const filterNode = (node, query) => {
    if (Array.isArray(node)) {
      const filtered = node.filter(s =>
        s.symbol.toLowerCase().includes(query) ||
        s.name.includes(query) ||
        (s.name_en || '').toLowerCase().includes(query)
      )
      return filtered.length > 0 ? filtered : null
    }
    const result = {}
    for (const [k, v] of Object.entries(node)) {
      const filtered = filterNode(v, query)
      if (filtered !== null) result[k] = filtered
    }
    return Object.keys(result).length > 0 ? result : null
  }

  const q = search.trim().toLowerCase()
  const filtered = q
    ? Object.fromEntries(
        Object.entries(categories)
          .map(([k, v]) => [k, filterNode(v, q)])
          .filter(([, v]) => v !== null)
      )
    : categories

  return (
    <div className="flex flex-col h-full bg-[#0A0A0A]">
      <div className="flex items-center gap-1 px-2 py-2 border-b border-[#2A2A2A]">
        <input
          type="text"
          placeholder="搜尋股票..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="flex-1 bg-[#1A1A1A] border border-[#2A2A2A] rounded px-2 py-1 text-[11px] text-gray-300 placeholder-gray-600 outline-none focus:border-blue-700"
        />
        <button
          onClick={() => {
            if (!keys.hasStock()) { onNeedKey?.(); return }
            setShowAddModal(true)
          }}
          className="flex-shrink-0 w-6 h-6 bg-blue-800 hover:bg-blue-700 text-white rounded text-xs flex items-center justify-center"
          title="新增自訂股票"
        >+</button>
        <button
          onClick={() => {
            if (!keys.hasStock()) { onNeedKey?.(); return }
            setShowEditor(true)
          }}
          className="flex-shrink-0 w-6 h-6 bg-[#1A2A1A] hover:bg-[#1A3A1A] text-green-400 rounded text-xs flex items-center justify-center"
          title="編輯自訂分類"
        >✎</button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {Object.entries(filtered).map(([key, val]) => (
          <TreeNode
            key={key}
            name={key}
            node={val}
            depth={0}
            onSelect={onSelect}
            selectedSymbol={selectedSymbol}
            onDelete={handleDeleteCustom}
            isCustom={key === '自訂觀察清單'}
          />
        ))}
      </div>

      {showAddModal && (
        <AddStockModal
          onClose={() => setShowAddModal(false)}
          onAdd={loadWatchlist}
        />
      )}

      {showEditor && (
        <WatchlistEditor
          onClose={() => setShowEditor(false)}
          onSaved={() => { setShowEditor(false); loadWatchlist() }}
        />
      )}
    </div>
  )
}
