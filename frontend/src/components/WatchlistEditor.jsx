import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/stocks.js'

const MAX_DEPTH = 4 // levels 0-4 = 5 levels of categories

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

// ── Small form components ─────────────────────────────────────────────────────

function InlineInput({ placeholder, onConfirm, onCancel, upper = false }) {
  const [val, setVal] = useState('')
  return (
    <div className="flex gap-1 items-center mt-0.5">
      <input
        autoFocus
        value={val}
        onChange={e => setVal(upper ? e.target.value.toUpperCase() : e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') onConfirm(val); if (e.key === 'Escape') onCancel() }}
        placeholder={placeholder}
        className="flex-1 min-w-0 bg-[#080808] border border-[#333] rounded px-2 py-0.5 text-[10px] text-white placeholder-gray-700 outline-none focus:border-blue-600"
      />
      <button onClick={() => onConfirm(val)} className="text-[9px] text-blue-400 hover:text-blue-200 flex-shrink-0">✓</button>
      <button onClick={onCancel} className="text-[9px] text-gray-600 hover:text-gray-300 flex-shrink-0">✕</button>
    </div>
  )
}

function AddStockForm({ onConfirm, onCancel }) {
  const [sym, setSym] = useState('')
  const [nm, setNm]   = useState('')
  return (
    <div className="mt-0.5 space-y-0.5">
      <input
        autoFocus
        value={sym}
        onChange={e => setSym(e.target.value.toUpperCase())}
        onKeyDown={e => e.key === 'Escape' && onCancel()}
        placeholder="代號（如 2330.TW 或 NVDA）"
        className="w-full bg-[#080808] border border-[#333] rounded px-2 py-0.5 text-[10px] text-white placeholder-gray-700 outline-none focus:border-blue-600"
      />
      <input
        value={nm}
        onChange={e => setNm(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') onConfirm(sym, nm); if (e.key === 'Escape') onCancel() }}
        placeholder="顯示名稱（選填）"
        className="w-full bg-[#080808] border border-[#333] rounded px-2 py-0.5 text-[10px] text-white placeholder-gray-700 outline-none focus:border-blue-600"
      />
      <div className="flex gap-2">
        <button onClick={() => onConfirm(sym, nm)} className="text-[9px] text-blue-400 hover:text-blue-200">確定</button>
        <button onClick={onCancel} className="text-[9px] text-gray-600 hover:text-gray-300">取消</button>
      </div>
    </div>
  )
}

// ── Stock row ─────────────────────────────────────────────────────────────────

function StockRow({ stock, indent, onEdit, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [sym, setSym] = useState(stock.symbol)
  const [nm,  setNm]  = useState(stock.name)

  if (editing) {
    return (
      <div style={{ paddingLeft: indent + 16 }} className="py-0.5 space-y-0.5 pr-2">
        <input autoFocus value={sym} onChange={e => setSym(e.target.value.toUpperCase())}
          className="w-full bg-[#080808] border border-[#333] rounded px-2 py-0.5 text-[10px] text-white outline-none focus:border-blue-600" />
        <input value={nm} onChange={e => setNm(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { onEdit(sym.trim(), nm.trim()); setEditing(false) } if (e.key === 'Escape') setEditing(false) }}
          className="w-full bg-[#080808] border border-[#333] rounded px-2 py-0.5 text-[10px] text-white outline-none focus:border-blue-600" />
        <div className="flex gap-2">
          <button onClick={() => { onEdit(sym.trim(), nm.trim()); setEditing(false) }} className="text-[9px] text-blue-400">確定</button>
          <button onClick={() => setEditing(false)} className="text-[9px] text-gray-600">取消</button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ paddingLeft: indent + 16 }} className="flex items-center gap-1 py-0.5 pr-2 group">
      <div className="flex-1 min-w-0">
        <span className="text-[10px] text-gray-300 truncate block">{stock.name}</span>
        <span className="text-[9px] text-gray-600">{stock.symbol}</span>
      </div>
      <div className="hidden group-hover:flex gap-1 flex-shrink-0">
        <button onClick={() => { setSym(stock.symbol); setNm(stock.name); setEditing(true) }}
          className="text-[9px] text-gray-500 hover:text-gray-200" title="編輯">✎</button>
        <button onClick={onDelete}
          className="text-[9px] text-gray-700 hover:text-red-400" title="刪除">✕</button>
      </div>
    </div>
  )
}

// ── Category node (recursive) ─────────────────────────────────────────────────

function CategoryNode({ name, value, path, depth, onChange }) {
  const [open,    setOpen]    = useState(true)
  const [renaming, setRenaming] = useState(false)
  const [renameVal, setRenameVal] = useState(name)
  const [adding,  setAdding]  = useState(null) // null | 'category' | 'stock'

  const isArray  = Array.isArray(value)
  const isEmpty  = !isArray && Object.keys(value || {}).length === 0
  const indent   = depth * 12 + 4

  const canAddSubcat = !isArray && depth < MAX_DEPTH
  const canAddStock  = isArray || isEmpty

  const update = (fn) => onChange(fn)

  const doRename = (newName) => {
    setRenaming(false)
    if (newName.trim() && newName.trim() !== name)
      update(tree => renameAt(tree, path, newName.trim()))
  }

  const doDelete = () => update(tree => deleteAt(tree, path))

  const doAddCategory = (catName) => {
    if (!catName.trim()) return
    setAdding(null)
    update(tree => setAt(tree, [...path, catName.trim()], {}))
  }

  const doAddStock = (sym, nm) => {
    if (!sym.trim()) return
    setAdding(null)
    const stock = { symbol: sym.trim().toUpperCase(), name: nm.trim() || sym.trim().toUpperCase() }
    if (isArray) {
      update(tree => setAt(tree, path, [...value, stock]))
    } else {
      update(tree => setAt(tree, path, [stock]))
    }
  }

  const doEditStock = (idx, sym, nm) => {
    update(tree => {
      const arr = getAt(tree, path)
      return setAt(tree, path, arr.map((s, i) => i === idx ? { symbol: sym || s.symbol, name: nm || sym || s.symbol } : s))
    })
  }

  const doDeleteStock = (idx) => {
    update(tree => setAt(tree, path, value.filter((_, i) => i !== idx)))
  }

  // depth-based label color
  const labelColors = [
    'text-blue-300 font-bold',
    'text-green-300 font-semibold',
    'text-yellow-200 font-medium',
    'text-[#9CDCFE]',
    'text-gray-400',
  ]
  const labelCls = labelColors[Math.min(depth, labelColors.length - 1)]

  return (
    <div>
      {/* Row */}
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
          >
            {name}
          </span>
        )}

        {/* Controls (hover-reveal) */}
        <div className="hidden group-hover:flex items-center gap-0.5 flex-shrink-0">
          <button onClick={() => { setRenameVal(name); setRenaming(true) }}
            className="text-[8px] text-gray-600 hover:text-gray-200 px-0.5" title="重命名">✎</button>
          {canAddSubcat && (
            <button onClick={() => { setOpen(true); setAdding('category') }}
              className="text-[8px] text-blue-700 hover:text-blue-400 px-0.5" title="新增子分類">+目錄</button>
          )}
          {canAddStock && (
            <button onClick={() => { setOpen(true); setAdding('stock') }}
              className="text-[8px] text-green-700 hover:text-green-400 px-0.5" title="新增股票">+股票</button>
          )}
          <button onClick={doDelete}
            className="text-[8px] text-gray-700 hover:text-red-400 px-0.5" title="刪除">✕</button>
        </div>
      </div>

      {/* Children */}
      {open && (
        <div>
          {/* Inline forms */}
          {adding === 'category' && (
            <div style={{ paddingLeft: indent + 12 }} className="pr-2 pb-1">
              <InlineInput placeholder="新分類名稱" onConfirm={doAddCategory} onCancel={() => setAdding(null)} />
            </div>
          )}
          {adding === 'stock' && (
            <div style={{ paddingLeft: indent + 12 }} className="pr-2 pb-1">
              <AddStockForm onConfirm={doAddStock} onCancel={() => setAdding(null)} />
            </div>
          )}

          {/* Stock list (leaf) */}
          {isArray && value.map((stock, idx) => (
            <StockRow
              key={idx}
              stock={stock}
              indent={indent}
              onEdit={(sym, nm) => doEditStock(idx, sym, nm)}
              onDelete={() => doDeleteStock(idx)}
            />
          ))}

          {/* Sub-categories */}
          {!isArray && Object.entries(value || {}).map(([childName, childVal]) => (
            <CategoryNode
              key={childName}
              name={childName}
              value={childVal}
              path={[...path, childName]}
              depth={depth + 1}
              onChange={onChange}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main editor modal ─────────────────────────────────────────────────────────

export default function WatchlistEditor({ onClose, onSaved }) {
  const [tree,       setTree]    = useState({})
  const [loading,    setLoading] = useState(true)
  const [saving,     setSaving]  = useState(false)
  const [msg,        setMsg]     = useState('')
  const [addingTop,  setAddingTop] = useState(false)

  useEffect(() => {
    api.getUserWatchlist()
      .then(d => setTree(d.watchlist || {}))
      .catch(() => setTree({}))
      .finally(() => setLoading(false))
  }, [])

  const handleChange = useCallback((fn) => setTree(prev => fn(prev)), [])

  const handleAddTop = (name) => {
    if (!name.trim()) return
    setAddingTop(false)
    setTree(prev => ({ ...prev, [name.trim()]: {} }))
  }

  const handleSave = async () => {
    setSaving(true); setMsg('')
    try {
      await api.saveUserWatchlist(tree)
      setMsg('✓ 已儲存')
      setTimeout(() => { setMsg(''); onSaved?.() }, 900)
    } catch (e) {
      setMsg('儲存失敗：' + e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-[#0D0D0D] border border-[#2A2A2A] rounded-lg shadow-2xl flex flex-col"
        style={{ width: 380, maxHeight: '85vh' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-[#222] flex-shrink-0">
          <span className="text-xs font-semibold text-white">編輯自訂分類</span>
          <div className="flex items-center gap-3">
            <span className="text-[9px] text-gray-600">雙擊名稱重命名 · 最多5層目錄</span>
            <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">×</button>
          </div>
        </div>

        {/* Tree */}
        <div className="flex-1 overflow-y-auto py-1 min-h-0">
          {loading ? (
            <div className="text-center text-gray-600 text-xs mt-10">載入中...</div>
          ) : (
            <>
              {Object.keys(tree).length === 0 && !addingTop && (
                <div className="text-center text-gray-700 text-xs mt-10 px-4">
                  尚無自訂分類<br />
                  <span className="text-gray-600">點擊下方「＋ 新增頂層分類」開始</span>
                </div>
              )}

              {Object.entries(tree).map(([name, val]) => (
                <CategoryNode
                  key={name}
                  name={name}
                  value={val}
                  path={[name]}
                  depth={0}
                  onChange={handleChange}
                />
              ))}

              {/* Add top-level category */}
              {addingTop ? (
                <div className="px-4 py-1">
                  <InlineInput
                    placeholder="頂層分類名稱"
                    onConfirm={handleAddTop}
                    onCancel={() => setAddingTop(false)}
                  />
                </div>
              ) : (
                <button
                  onClick={() => setAddingTop(true)}
                  className="w-full text-left px-4 py-1.5 text-[10px] text-gray-700 hover:text-gray-300 hover:bg-[#151515] border-t border-[#1A1A1A] mt-1"
                >
                  ＋ 新增頂層分類
                </button>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-3 px-3 py-2 border-t border-[#222] flex-shrink-0">
          {msg ? (
            <span className={`text-[10px] flex-1 ${msg.startsWith('✓') ? 'text-green-400' : 'text-red-400'}`}>{msg}</span>
          ) : (
            <span className="text-[9px] text-gray-700 flex-1">懸停分類可見操作按鈕</span>
          )}
          <button onClick={onClose} className="px-3 py-1 text-xs border border-[#333] text-gray-400 hover:text-white rounded">取消</button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1 text-xs bg-blue-700 hover:bg-blue-600 text-white rounded disabled:opacity-50"
          >
            {saving ? '儲存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}
