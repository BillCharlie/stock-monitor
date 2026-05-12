import { useEffect, useState, useCallback, createContext, useContext } from 'react'
import { api, keys } from '../api/stocks.js'

const MAX_DEPTH = 4

// ── Immutable tree helpers ────────────────────────────────────────────────────
function getAt(obj, path) {
  return path.reduce((o, k) => (o != null ? o[k] : undefined), obj)
}
function setAt(obj, path, val) {
  if (!path.length) return val
  const [h, ...rest] = path
  return { ...obj, [h]: setAt(obj != null && h in obj ? obj[h] : {}, rest, val) }
}
function deleteAt(obj, path) {
  if (path.length === 1) {
    const { [path[0]]: _, ...rest } = obj
    return rest
  }
  const [h, ...rest] = path
  return { ...obj, [h]: deleteAt(obj[h], rest) }
}
function renameAt(obj, path, newName) {
  const n = newName.trim()
  const old = path.at(-1)
  if (!n || n === old) return obj
  const parentPath = path.slice(0, -1)
  const parent = parentPath.length ? getAt(obj, parentPath) : obj
  if (n in parent) return obj
  const rebuilt = {}
  for (const [k, v] of Object.entries(parent)) rebuilt[k === old ? n : k] = v
  return parentPath.length ? setAt(obj, parentPath, rebuilt) : rebuilt
}

// ── Depth-based style config ──────────────────────────────────────────────────
const DEPTH_STYLES = [
  'bg-[#0F1A2A] text-blue-300 font-bold text-[11px] uppercase tracking-wide border-b border-[#1A2A3A]',
  'bg-[#111B11] text-green-300 font-semibold text-[11px] border-b border-[#1A2A1A]',
  'bg-[#141414] text-yellow-200 font-medium text-[10px] border-b border-[#222]',
  'bg-[#0D0D0D] text-[#9CDCFE] text-[10px] border-b border-[#1A1A1A]',
  'bg-[#0A0A0A] text-gray-500 text-[10px] border-b border-[#181818]',
]

// ── Edit context ──────────────────────────────────────────────────────────────
const EditCtx = createContext(null)

// ── Inline input ──────────────────────────────────────────────────────────────
function InlineInput({ placeholder, onConfirm, onCancel, upper = false }) {
  const [val, setVal] = useState('')
  return (
    <div className="flex gap-1 items-center py-0.5">
      <input
        autoFocus
        value={val}
        onChange={e => setVal(upper ? e.target.value.toUpperCase() : e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') onConfirm(val); if (e.key === 'Escape') onCancel() }}
        placeholder={placeholder}
        className="flex-1 min-w-0 bg-[#080808] border border-[#333] rounded px-1.5 py-0.5 text-[10px] text-white placeholder-gray-700 outline-none focus:border-blue-600"
      />
      <button onClick={() => onConfirm(val)} className="text-[9px] text-blue-400 hover:text-blue-200 flex-shrink-0">✓</button>
      <button onClick={onCancel} className="text-[9px] text-gray-600 hover:text-gray-300 flex-shrink-0">✕</button>
    </div>
  )
}

// ── Add stock form ────────────────────────────────────────────────────────────
function AddStockForm({ onConfirm, onCancel }) {
  const [sym, setSym] = useState('')
  const [nm, setNm] = useState('')
  return (
    <div className="space-y-0.5 py-0.5">
      <input
        autoFocus
        value={sym}
        onChange={e => setSym(e.target.value.toUpperCase())}
        onKeyDown={e => e.key === 'Escape' && onCancel()}
        placeholder="代號（如 2330.TW 或 NVDA）"
        className="w-full bg-[#080808] border border-[#333] rounded px-1.5 py-0.5 text-[10px] text-white placeholder-gray-700 outline-none focus:border-blue-600"
      />
      <input
        value={nm}
        onChange={e => setNm(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') onConfirm(sym, nm); if (e.key === 'Escape') onCancel() }}
        placeholder="顯示名稱（選填）"
        className="w-full bg-[#080808] border border-[#333] rounded px-1.5 py-0.5 text-[10px] text-white placeholder-gray-700 outline-none focus:border-blue-600"
      />
      <div className="flex gap-2">
        <button onClick={() => onConfirm(sym, nm)} className="text-[9px] text-blue-400 hover:text-blue-200">確定</button>
        <button onClick={onCancel} className="text-[9px] text-gray-600 hover:text-gray-300">取消</button>
      </div>
    </div>
  )
}

// ── Display-mode stock row (+ optional drag handle in edit mode) ──────────────
function DisplayStockRow({ stock, isSelected, onClick, onDelete, depth, isDraggable }) {
  const [quote, setQuote] = useState(null)
  const indent = Math.min(depth, 5) * 10 + 8
  const ctx = useContext(EditCtx)

  useEffect(() => {
    let cancelled = false
    api.getQuote(stock.symbol).then(q => { if (!cancelled) setQuote(q) }).catch(() => {})
    return () => { cancelled = true }
  }, [stock.symbol])

  const isUp = quote?.change_pct >= 0
  const priceColor = quote ? (isUp ? 'text-[#EF5350]' : 'text-[#26A69A]') : 'text-gray-600'

  return (
    <div
      className={`flex items-center py-1 pr-2 cursor-pointer hover:bg-[#1A1A1A] transition-colors ${
        isSelected ? 'bg-[#1A2A3A] border-l-2 border-blue-500' : 'border-l-2 border-transparent'
      }`}
      style={{ paddingLeft: indent }}
      onClick={onClick}
      draggable={isDraggable || undefined}
      onDragStart={isDraggable ? (e) => {
        e.stopPropagation()
        ctx?.setDragItem({ stock, sourcePath: null, sourceIdx: null })
      } : undefined}
      onDragEnd={isDraggable ? () => ctx?.setDragItem(null) : undefined}
    >
      {isDraggable && (
        <span className="text-gray-700 text-[10px] mr-1 cursor-grab flex-shrink-0 select-none">⠿</span>
      )}
      <div className="flex flex-col min-w-0 flex-1">
        <span className="text-[11px] text-gray-200 truncate">{stock.name}</span>
        {stock.tags?.length > 0 && (
          <span className="text-[9px] text-[#4A7A6A] truncate leading-tight">{stock.tags.join(' · ')}</span>
        )}
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

// ── Display-mode tree node (read-only; used for normal view + edit-mode built-ins) ──
function DisplayTreeNode({ name, node, depth, onSelect, selectedSymbol, onDelete, isCustom, isDragSource }) {
  const [collapsed, setCollapsed] = useState(depth >= 2)
  const styleIdx = Math.min(depth, DEPTH_STYLES.length - 1)
  const indent = depth * 8

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
        {!collapsed && node.map(stock => (
          <DisplayStockRow
            key={stock.symbol}
            stock={stock}
            depth={depth + 1}
            isSelected={selectedSymbol === stock.symbol}
            onClick={() => onSelect(stock.symbol, stock.name)}
            onDelete={isCustom ? onDelete : null}
            isDraggable={isDragSource}
          />
        ))}
      </div>
    )
  }

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
      {!collapsed && Object.entries(node).map(([key, val]) => (
        <DisplayTreeNode
          key={key}
          name={key}
          node={val}
          depth={depth + 1}
          onSelect={onSelect}
          selectedSymbol={selectedSymbol}
          onDelete={onDelete}
          isCustom={isCustom}
          isDragSource={isDragSource}
        />
      ))}
    </div>
  )
}

// ── Edit-mode: user stock row (drag handle + edit/delete) ─────────────────────
function UserStockRow({ stock, path, idx, depth }) {
  const { setUserTree, setDragItem } = useContext(EditCtx)
  const [editing, setEditing] = useState(false)
  const [sym, setSym] = useState(stock.symbol)
  const [nm, setNm] = useState(stock.name)
  const indent = Math.min(depth, 5) * 10 + 20

  const doDelete = () => setUserTree(t => {
    const arr = getAt(t, path)
    return setAt(t, path, arr.filter((_, i) => i !== idx))
  })

  const doEdit = () => {
    if (!sym.trim()) return
    setUserTree(t => {
      const arr = getAt(t, path)
      return setAt(t, path, arr.map((s, i) =>
        i === idx ? { symbol: sym.trim().toUpperCase(), name: nm.trim() || sym.trim().toUpperCase() } : s
      ))
    })
    setEditing(false)
  }

  if (editing) {
    return (
      <div style={{ paddingLeft: indent }} className="pr-2 py-0.5 space-y-0.5">
        <input autoFocus value={sym} onChange={e => setSym(e.target.value.toUpperCase())}
          className="w-full bg-[#080808] border border-[#333] rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-blue-600" />
        <input value={nm} onChange={e => setNm(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') doEdit(); if (e.key === 'Escape') setEditing(false) }}
          className="w-full bg-[#080808] border border-[#333] rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-blue-600" />
        <div className="flex gap-2">
          <button onClick={doEdit} className="text-[9px] text-blue-400">確定</button>
          <button onClick={() => setEditing(false)} className="text-[9px] text-gray-600">取消</button>
        </div>
      </div>
    )
  }

  return (
    <div
      style={{ paddingLeft: indent }}
      className="flex items-center gap-1 py-0.5 pr-2 group hover:bg-[#1A1A1A]"
      draggable
      onDragStart={e => { e.stopPropagation(); setDragItem({ stock, sourcePath: path, sourceIdx: idx }) }}
      onDragEnd={() => setDragItem(null)}
    >
      <span className="text-gray-600 text-[10px] cursor-grab flex-shrink-0 select-none">⠿</span>
      <div className="flex-1 min-w-0">
        <span className="text-[10px] text-gray-300 truncate block">{stock.name}</span>
        <span className="text-[9px] text-gray-600">{stock.symbol}</span>
      </div>
      <div className="hidden group-hover:flex gap-1 flex-shrink-0">
        <button onClick={() => { setSym(stock.symbol); setNm(stock.name); setEditing(true) }}
          className="text-[9px] text-gray-500 hover:text-gray-200">✎</button>
        <button onClick={doDelete}
          className="text-[9px] text-gray-700 hover:text-red-400">✕</button>
      </div>
    </div>
  )
}

// ── Edit-mode: user category node (editable, DnD drop target) ────────────────
function UserCatNode({ name, value, path, depth }) {
  const { setUserTree, dragItem, setDragItem, dropPath, setDropPath } = useContext(EditCtx)
  const [open, setOpen] = useState(true)
  const [renaming, setRenaming] = useState(false)
  const [renameVal, setRenameVal] = useState(name)
  const [adding, setAdding] = useState(null) // null | 'category' | 'stock'

  const isArray = Array.isArray(value)
  const isEmpty = !isArray && Object.keys(value || {}).length === 0
  const canAcceptDrop = isArray || isEmpty
  const canAddSubcat = !isArray && depth < MAX_DEPTH
  const isDropTarget = canAcceptDrop && dropPath != null && dropPath.join('|') === path.join('|')
  const indent = depth * 10 + 4

  const labelColors = [
    'text-blue-300 font-bold',
    'text-green-300 font-semibold',
    'text-yellow-200 font-medium',
    'text-[#9CDCFE]',
    'text-gray-400',
  ]
  const labelCls = labelColors[Math.min(depth, labelColors.length - 1)]

  const doRename = (newName) => {
    setRenaming(false)
    if (newName.trim() && newName.trim() !== name)
      setUserTree(t => renameAt(t, path, newName.trim()))
  }
  const doDelete = () => setUserTree(t => deleteAt(t, path))
  const doAddCategory = (catName) => {
    if (!catName.trim()) return
    setAdding(null)
    setUserTree(t => setAt(t, [...path, catName.trim()], {}))
  }
  const doAddStock = (sym, nm) => {
    if (!sym.trim()) return
    setAdding(null)
    const stock = { symbol: sym.trim().toUpperCase(), name: nm.trim() || sym.trim().toUpperCase() }
    setUserTree(t => {
      const cur = getAt(t, path)
      if (Array.isArray(cur)) return setAt(t, path, [...cur, stock])
      return setAt(t, path, [stock])
    })
  }

  const handleDragOver = (e) => {
    if (!dragItem || !canAcceptDrop) return
    e.preventDefault()
    e.stopPropagation()
    setDropPath(path)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDropPath(null)
    if (!dragItem || !canAcceptDrop) return
    const { stock, sourcePath, sourceIdx } = dragItem
    setDragItem(null)
    if (sourcePath?.join('|') === path.join('|')) return
    setUserTree(t => {
      let tree = t
      const cur = getAt(tree, path)
      if (Array.isArray(cur)) {
        if (cur.find(s => s.symbol === stock.symbol)) return tree
        tree = setAt(tree, path, [...cur, stock])
      } else {
        tree = setAt(tree, path, [stock])
      }
      if (sourcePath != null) {
        const srcArr = getAt(tree, sourcePath)
        if (Array.isArray(srcArr))
          tree = setAt(tree, sourcePath, srcArr.filter((_, i) => i !== sourceIdx))
      }
      return tree
    })
  }

  return (
    <div
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      className={isDropTarget ? 'ring-1 ring-inset ring-blue-500/50 bg-blue-900/10' : ''}
    >
      <div
        className="flex items-center gap-1 py-0.5 pr-2 group hover:bg-[#1A1A1A] cursor-pointer"
        style={{ paddingLeft: indent }}
      >
        <span onClick={() => setOpen(o => !o)} className="text-gray-600 text-[9px] w-2.5 flex-shrink-0 select-none">
          {open ? '▾' : '▸'}
        </span>

        {renaming ? (
          <input
            autoFocus
            value={renameVal}
            onChange={e => setRenameVal(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') doRename(renameVal); if (e.key === 'Escape') setRenaming(false) }}
            onBlur={() => doRename(renameVal)}
            className="flex-1 min-w-0 bg-[#080808] border border-[#2A5A8A] rounded px-1 text-[10px] text-white outline-none"
          />
        ) : (
          <span
            className={`flex-1 min-w-0 text-[10px] truncate select-none ${labelCls}`}
            onClick={() => setOpen(o => !o)}
            onDoubleClick={() => { setRenameVal(name); setRenaming(true) }}
          >{name}</span>
        )}

        <div className="hidden group-hover:flex items-center gap-0.5 flex-shrink-0">
          <button onClick={() => { setRenameVal(name); setRenaming(true) }}
            className="text-[8px] text-gray-600 hover:text-gray-200 px-0.5" title="重命名">✎</button>
          {canAddSubcat && (
            <button onClick={() => { setOpen(true); setAdding('category') }}
              className="text-[8px] text-blue-700 hover:text-blue-400 px-0.5">+目錄</button>
          )}
          <button onClick={() => { setOpen(true); setAdding('stock') }}
            className="text-[8px] text-green-700 hover:text-green-400 px-0.5">+股票</button>
          <button onClick={doDelete}
            className="text-[8px] text-gray-700 hover:text-red-400 px-0.5">✕</button>
        </div>
      </div>

      {open && (
        <div>
          {adding === 'category' && (
            <div style={{ paddingLeft: indent + 12 }} className="pr-2">
              <InlineInput placeholder="新分類名稱" onConfirm={doAddCategory} onCancel={() => setAdding(null)} />
            </div>
          )}
          {adding === 'stock' && (
            <div style={{ paddingLeft: indent + 12 }} className="pr-2">
              <AddStockForm onConfirm={doAddStock} onCancel={() => setAdding(null)} />
            </div>
          )}
          {isArray
            ? value.map((stock, idx) => (
                <UserStockRow key={idx} stock={stock} path={path} idx={idx} depth={depth + 1} />
              ))
            : Object.entries(value || {}).map(([childName, childVal]) => (
                <UserCatNode
                  key={childName}
                  name={childName}
                  value={childVal}
                  path={[...path, childName]}
                  depth={depth + 1}
                />
              ))
          }
        </div>
      )}
    </div>
  )
}

// ── Add stock modal ───────────────────────────────────────────────────────────
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

// ── Main WatchlistPanel ───────────────────────────────────────────────────────
export default function WatchlistPanel({ onSelect, selectedSymbol, onNeedKey }) {
  const [categories, setCategories] = useState({})
  const [search, setSearch] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [userTree, setUserTree] = useState({})
  const [loadingEdit, setLoadingEdit] = useState(false)
  const [addingTop, setAddingTop] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [dragItem, setDragItem] = useState(null)
  const [dropPath, setDropPath] = useState(null)

  const loadWatchlist = useCallback(() => {
    api.getWatchlist().then(data => setCategories(data.categories || {})).catch(() => {})
  }, [])

  useEffect(() => { loadWatchlist() }, [loadWatchlist])

  const enterEditMode = async () => {
    if (!keys.hasStock()) { onNeedKey?.(); return }
    setLoadingEdit(true)
    try {
      const d = await api.getUserWatchlist()
      setUserTree(d.watchlist || {})
    } catch {
      setUserTree({})
    } finally {
      setLoadingEdit(false)
      setEditMode(true)
    }
  }

  const exitEditMode = () => {
    setEditMode(false)
    setDragItem(null)
    setDropPath(null)
    setSaveMsg('')
    setAddingTop(false)
  }

  const handleSave = async () => {
    setSaving(true)
    setSaveMsg('')
    try {
      await api.saveUserWatchlist(userTree)
      setSaveMsg('✓ 已儲存')
      setTimeout(() => { setSaveMsg(''); exitEditMode(); loadWatchlist() }, 900)
    } catch (e) {
      setSaveMsg('儲存失敗：' + e.message)
    } finally {
      setSaving(false)
    }
  }

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
        (s.name_en || '').toLowerCase().includes(query) ||
        (s.tags || []).some(t => t.toLowerCase().includes(query))
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

  // In edit mode: user-defined keys vs built-in keys
  const userKeys = new Set(Object.keys(userTree))
  const builtinEntries = Object.entries(categories).filter(([k]) => !userKeys.has(k))

  const ctxValue = { setUserTree, dragItem, setDragItem, dropPath, setDropPath }

  return (
    <div className="flex flex-col h-full bg-[#0A0A0A]">
      {/* Header */}
      <div className="flex items-center gap-1 px-2 py-2 border-b border-[#2A2A2A] flex-shrink-0">
        {!editMode ? (
          <>
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
              onClick={enterEditMode}
              disabled={loadingEdit}
              className="flex-shrink-0 w-6 h-6 bg-[#1A2A1A] hover:bg-[#1A3A1A] text-green-400 rounded text-xs flex items-center justify-center disabled:opacity-50"
              title="編輯自訂分類"
            >✎</button>
          </>
        ) : (
          <div className="flex items-center w-full gap-1">
            <span className="text-[10px] text-green-400 font-medium">✎ 編輯模式</span>
            <span className="text-[9px] text-gray-700 flex-1 ml-1">雙擊重命名 · 拖曳移動</span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {!editMode ? (
          Object.entries(filtered).map(([key, val]) => (
            <DisplayTreeNode
              key={key}
              name={key}
              node={val}
              depth={0}
              onSelect={onSelect}
              selectedSymbol={selectedSymbol}
              onDelete={handleDeleteCustom}
              isCustom={key === '自訂觀察清單'}
              isDragSource={false}
            />
          ))
        ) : (
          <EditCtx.Provider value={ctxValue}>
            {/* User tree (editable) */}
            {Object.keys(userTree).length === 0 && !addingTop && (
              <div className="text-center text-gray-700 text-[10px] mt-6 px-4">
                尚無自訂分類<br />
                <span className="text-[9px] text-gray-600">點擊下方新增，或從內建分類拖入股票</span>
              </div>
            )}
            {Object.entries(userTree).map(([name, val]) => (
              <UserCatNode key={name} name={name} value={val} path={[name]} depth={0} />
            ))}

            {/* Add top-level category */}
            {addingTop ? (
              <div className="px-3 py-1">
                <InlineInput
                  placeholder="頂層分類名稱"
                  onConfirm={(name) => {
                    if (!name.trim()) return
                    setAddingTop(false)
                    setUserTree(t => ({ ...t, [name.trim()]: {} }))
                  }}
                  onCancel={() => setAddingTop(false)}
                />
              </div>
            ) : (
              <button
                onClick={() => setAddingTop(true)}
                className="w-full text-left px-3 py-1.5 text-[10px] text-gray-700 hover:text-gray-300 hover:bg-[#151515] border-b border-[#1A1A1A]"
              >＋ 新增頂層分類</button>
            )}

            {/* Built-in categories (drag sources only) */}
            {builtinEntries.length > 0 && (
              <>
                <div className="px-3 pt-2 pb-1">
                  <div className="border-t border-[#222]" />
                  <span className="text-[9px] text-gray-700 block mt-1">內建分類（拖曳股票至上方自訂區）</span>
                </div>
                {builtinEntries.map(([key, val]) => (
                  <DisplayTreeNode
                    key={key}
                    name={key}
                    node={val}
                    depth={0}
                    onSelect={onSelect}
                    selectedSymbol={selectedSymbol}
                    onDelete={null}
                    isCustom={false}
                    isDragSource={true}
                  />
                ))}
              </>
            )}
          </EditCtx.Provider>
        )}
      </div>

      {/* Edit mode footer */}
      {editMode && (
        <div className="flex items-center gap-2 px-2 py-2 border-t border-[#2A2A2A] flex-shrink-0">
          {saveMsg ? (
            <span className={`text-[10px] flex-1 ${saveMsg.startsWith('✓') ? 'text-green-400' : 'text-red-400'}`}>
              {saveMsg}
            </span>
          ) : (
            <span className="text-[9px] text-gray-700 flex-1">懸停分類可見操作按鈕</span>
          )}
          <button onClick={exitEditMode}
            className="px-2 py-1 text-[10px] border border-[#333] text-gray-400 hover:text-white rounded">
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-2 py-1 text-[10px] bg-blue-700 hover:bg-blue-600 text-white rounded disabled:opacity-50"
          >
            {saving ? '儲存中...' : '保存'}
          </button>
        </div>
      )}

      {showAddModal && (
        <AddStockModal
          onClose={() => setShowAddModal(false)}
          onAdd={loadWatchlist}
        />
      )}
    </div>
  )
}
