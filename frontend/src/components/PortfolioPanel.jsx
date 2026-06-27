import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/stocks.js'

const DEFAULT_PEOPLE = ['Fiona', 'Bill', 'Yang']

// Project color convention: gains red, losses green.
const GAIN = '#EF5350'
const LOSS = '#26A69A'
const FLAT = '#FFA726'

const todayStr = () => new Date().toISOString().slice(0, 10)
const num = (v) => {
  const n = parseFloat(v)
  return Number.isFinite(n) ? n : null
}
const fmtMoney = (n) =>
  n == null ? '—' : n.toLocaleString('en-US', { maximumFractionDigits: 0 })
const fmtPts = (n) => (n == null ? '—' : (n >= 0 ? '+' : '') + n.toFixed(2))
// Invested amount is derived: 買入點 × 股數
const calcAmount = (price, shares) =>
  price != null && shares != null ? price * shares : null

// Aggregate a holding's lots: total shares/amount and weighted average buy price.
const holdingStats = (h) => {
  let totalShares = 0, totalAmount = 0
  for (const l of h.lots || []) {
    const shares = l.shares
    const amount = l.amount != null ? l.amount : calcAmount(l.price, l.shares)
    if (shares != null) totalShares += shares
    if (amount != null) totalAmount += amount
  }
  const avg = totalShares > 0 ? totalAmount / totalShares : null
  return { totalShares, totalAmount, avg }
}
const round2 = (n) => (n == null ? null : Math.round(n * 100) / 100)
// Stop-loss / take-profit price from average and a percentage.
const stopLossPrice = (avg, pct) =>
  avg != null && pct != null ? round2(avg * (1 - pct / 100)) : null
const takeProfitPrice = (avg, pct) =>
  avg != null && pct != null ? round2(avg * (1 + pct / 100)) : null

// Flatten the nested watchlist response into a name -> {symbol, name} index.
function buildNameIndex(categories) {
  const byName = new Map()
  const list = []
  const walk = (node) => {
    if (Array.isArray(node)) {
      node.forEach(walk)
    } else if (node && typeof node === 'object') {
      if (node.symbol) {
        const entry = { symbol: node.symbol, name: node.name || node.symbol }
        list.push(entry)
        if (node.name) byName.set(node.name, entry)
        byName.set(node.symbol, entry)
      } else {
        Object.values(node).forEach(walk)
      }
    }
  }
  walk(categories || {})
  return { byName, list }
}

export default function PortfolioPanel({ onJumpToChart }) {
  const [persons, setPersons] = useState({})
  const [activePerson, setActivePerson] = useState('')
  const [nameIndex, setNameIndex] = useState({ byName: new Map(), list: [] })
  const [quotes, setQuotes] = useState({})        // symbol -> price (今日收盤)
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')
  const [newPerson, setNewPerson] = useState('')

  // New-holding form (amount is derived from price × shares)
  const [form, setForm] = useState({ name: '', symbol: '', price: '', shares: '', date: todayStr() })
  // Add-lot form keyed by holding index
  const [lotForms, setLotForms] = useState({})

  // ── Initial load ────────────────────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const [pf, wl] = await Promise.all([
          api.getPortfolios().catch(() => ({ persons: {} })),
          api.getWatchlist().catch(() => ({ categories: {} })),
        ])
        const p = pf.persons || {}
        setPersons(p)
        setNameIndex(buildNameIndex(wl.categories))
        const first = Object.keys(p)[0] || ''
        setActivePerson(first)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  // ── Fetch today's close for all symbols of the active person ─────────────────
  const activeHoldings = persons[activePerson] || []
  useEffect(() => {
    const symbols = [...new Set(activeHoldings.map(h => h.symbol))]
    const missing = symbols.filter(s => quotes[s] === undefined)
    if (!missing.length) return
    let cancelled = false
    ;(async () => {
      for (const s of missing) {
        try {
          const q = await api.getQuote(s)
          if (!cancelled) setQuotes(prev => ({ ...prev, [s]: q?.price ?? null }))
        } catch {
          if (!cancelled) setQuotes(prev => ({ ...prev, [s]: null }))
        }
      }
    })()
    return () => { cancelled = true }
  }, [activeHoldings, quotes])

  // ── Persist helper ───────────────────────────────────────────────────────────
  const persist = useCallback(async (next) => {
    setPersons(next)
    setMsg('儲存中...')
    try {
      await api.savePortfolios(next)
      setMsg('✓ 已儲存')
      setTimeout(() => setMsg(m => (m === '✓ 已儲存' ? '' : m)), 1500)
    } catch (e) {
      if (String(e.message).includes('401') || e.message.includes('密鑰')) {
        setMsg('⚠ 密鑰錯誤，無法儲存')
      } else {
        setMsg('⚠ 儲存失敗：' + e.message)
      }
    }
  }, [])

  // ── Person actions ────────────────────────────────────────────────────────────
  const addPerson = (name) => {
    const n = (name || '').trim()
    if (!n || persons[n]) { setActivePerson(n || activePerson); return }
    const next = { ...persons, [n]: [] }
    setActivePerson(n)
    setNewPerson('')
    persist(next)
  }

  const removePerson = (name) => {
    if (!window.confirm(`確定刪除「${name}」的所有持股紀錄？`)) return
    const next = { ...persons }
    delete next[name]
    const remaining = Object.keys(next)
    setActivePerson(remaining[0] || '')
    persist(next)
  }

  // ── Holding / lot actions ──────────────────────────────────────────────────────
  const resolveSymbol = (name) => nameIndex.byName.get(name.trim())?.symbol || ''

  const onFormName = (name) => {
    const sym = resolveSymbol(name)
    setForm(f => ({ ...f, name, symbol: sym || f.symbol }))
  }

  const addHolding = () => {
    const symbol = (form.symbol || '').trim().toUpperCase()
    const name = form.name.trim() || nameIndex.byName.get(symbol)?.name || symbol
    if (!symbol) { setMsg('請輸入股票名稱或代號'); return }
    const price = num(form.price), shares = num(form.shares)
    const lot = {
      price, shares, amount: calcAmount(price, shares),
      date: form.date || todayStr(),
    }
    const holdings = [...(persons[activePerson] || [])]
    const idx = holdings.findIndex(h => h.symbol === symbol)
    if (idx >= 0) {
      holdings[idx] = { ...holdings[idx], lots: [...holdings[idx].lots, lot] }
    } else {
      holdings.push({ symbol, name, lots: [lot] })
    }
    persist({ ...persons, [activePerson]: holdings })
    setForm({ name: '', symbol: '', price: '', shares: '', date: todayStr() })
  }

  const addLot = (hIdx) => {
    const lf = lotForms[hIdx] || {}
    const price = num(lf.price), shares = num(lf.shares)
    const lot = { price, shares, amount: calcAmount(price, shares), date: lf.date || todayStr() }
    const holdings = persons[activePerson].map((h, i) =>
      i === hIdx ? { ...h, lots: [...h.lots, lot] } : h
    )
    persist({ ...persons, [activePerson]: holdings })
    setLotForms(prev => ({ ...prev, [hIdx]: { date: todayStr() } }))
  }

  const removeLot = (hIdx, lIdx) => {
    const holdings = persons[activePerson]
      .map((h, i) => i === hIdx ? { ...h, lots: h.lots.filter((_, j) => j !== lIdx) } : h)
      .filter(h => h.lots.length > 0)
    persist({ ...persons, [activePerson]: holdings })
  }

  const removeHolding = (hIdx) => {
    const holdings = persons[activePerson].filter((_, i) => i !== hIdx)
    persist({ ...persons, [activePerson]: holdings })
  }

  // Patch a holding locally (e.g. stop-loss/take-profit %); save on blur.
  const patchHolding = (hIdx, patch) => {
    setPersons(prev => ({
      ...prev,
      [activePerson]: (prev[activePerson] || []).map((h, i) => i === hIdx ? { ...h, ...patch } : h),
    }))
  }
  const saveNow = () => persist(persons)

  // ── Jump to chart with buy-point marks + reference levels ───────────────────────
  const jumpLot = (h, lot) =>
    onJumpToChart?.(h.symbol, h.name,
      lot.price != null ? [{ time: lot.date, price: lot.price, label: lot.date }] : [], [])

  const holdingLevels = (h) => {
    const { avg } = holdingStats(h)
    const levels = []
    if (avg != null) levels.push({ price: round2(avg), color: '#40C4FF', title: `均價 ${round2(avg)}`, dashed: false })
    const sl = stopLossPrice(avg, num(h.stopLossPct))
    if (sl != null) levels.push({ price: sl, color: LOSS, title: `停損 ${sl}`, dashed: true })
    const tp = takeProfitPrice(avg, num(h.takeProfitPct))
    if (tp != null) levels.push({ price: tp, color: GAIN, title: `停漲 ${tp}`, dashed: true })
    return levels
  }

  const jumpHolding = (h) =>
    onJumpToChart?.(h.symbol, h.name,
      h.lots.filter(l => l.price != null).map(l => ({ time: l.date, price: l.price, label: l.date })),
      holdingLevels(h))

  const lotPL = (lot, close) => {
    if (lot.price == null || close == null) return { pts: null, money: null }
    const pts = close - lot.price
    const money = lot.shares != null ? pts * lot.shares : null
    return { pts, money }
  }

  const peopleToOffer = DEFAULT_PEOPLE.filter(p => !persons[p])

  if (loading) {
    return <div className="h-full flex items-center justify-center text-gray-500 text-sm">載入中...</div>
  }

  return (
    <div className="h-full overflow-y-auto bg-[#0D0D0D] text-gray-200">
      <datalist id="portfolio-stock-names">
        {nameIndex.list.map(e => (
          <option key={e.symbol} value={e.name}>{e.symbol}</option>
        ))}
      </datalist>

      <div className="p-4 max-w-[1100px] mx-auto">
        {/* Header */}
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <h2 className="text-white font-semibold text-base mr-2">資產管理</h2>
          {msg && (
            <span className={`text-xs ${msg.startsWith('⚠') ? 'text-yellow-400' : 'text-green-400'}`}>
              {msg}
            </span>
          )}
        </div>

        {/* Person tabs */}
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          {Object.keys(persons).map(p => (
            <span key={p} className="inline-flex items-center">
              <button
                onClick={() => setActivePerson(p)}
                className={`px-3 py-1 rounded-l text-xs transition-colors ${
                  activePerson === p ? 'bg-blue-700 text-white' : 'bg-[#1A1A1A] text-gray-400 hover:text-white'
                }`}
              >
                {p}
              </button>
              <button
                onClick={() => removePerson(p)}
                title="刪除此人"
                className={`px-1.5 py-1 rounded-r text-xs ${
                  activePerson === p ? 'bg-blue-800 text-blue-200' : 'bg-[#151515] text-gray-600 hover:text-red-400'
                }`}
              >
                ×
              </button>
            </span>
          ))}

          {peopleToOffer.map(p => (
            <button
              key={p}
              onClick={() => addPerson(p)}
              className="px-2 py-1 rounded text-xs border border-dashed border-[#333] text-gray-500 hover:text-white hover:border-gray-500"
            >
              + {p}
            </button>
          ))}

          <span className="inline-flex items-center gap-1">
            <input
              value={newPerson}
              onChange={e => setNewPerson(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addPerson(newPerson)}
              placeholder="新增人員..."
              className="w-24 bg-[#0D0D0D] border border-[#333] rounded px-2 py-1 text-xs text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={() => addPerson(newPerson)}
              className="px-2 py-1 rounded text-xs bg-[#1B5E20] text-green-300 hover:bg-[#2E7D32]"
            >
              新增
            </button>
          </span>
        </div>

        {!activePerson ? (
          <p className="text-gray-500 text-sm">請先新增一位人員（如 Fiona、Bill、Yang）。</p>
        ) : (
          <>
            {/* Add-holding form */}
            <div className="bg-[#141414] border border-[#222] rounded p-3 mb-4">
              <p className="text-xs text-gray-400 mb-2">為「{activePerson}」新增持股（輸入股票名稱會自動帶出代號）</p>
              <div className="flex gap-2 flex-wrap items-end">
                <Field label="股票名稱">
                  <input
                    list="portfolio-stock-names"
                    value={form.name}
                    onChange={e => onFormName(e.target.value)}
                    placeholder="如 台積電"
                    className="w-32 input"
                  />
                </Field>
                <Field label="代號">
                  <input
                    value={form.symbol}
                    onChange={e => setForm(f => ({ ...f, symbol: e.target.value }))}
                    placeholder="自動 / 手填"
                    className="w-28 input"
                  />
                </Field>
                <Field label="買入點">
                  <input value={form.price} onChange={e => setForm(f => ({ ...f, price: e.target.value }))} type="number" className="w-20 input" />
                </Field>
                <Field label="股數">
                  <input value={form.shares} onChange={e => setForm(f => ({ ...f, shares: e.target.value }))} type="number" className="w-20 input" />
                </Field>
                <Field label="投資資金（自動）">
                  <div className="w-24 px-2 py-1 text-xs text-gray-400 bg-[#0A0A0A] border border-[#222] rounded">
                    {fmtMoney(calcAmount(num(form.price), num(form.shares)))}
                  </div>
                </Field>
                <Field label="日期">
                  <input value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} type="date" className="w-36 input" />
                </Field>
                <button
                  onClick={addHolding}
                  className="px-3 py-1.5 rounded text-xs bg-blue-700 hover:bg-blue-600 text-white"
                >
                  新增持股
                </button>
              </div>
            </div>

            {/* Holdings table */}
            {activeHoldings.length === 0 ? (
              <p className="text-gray-500 text-sm">尚無持股，請於上方新增。</p>
            ) : (
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="text-gray-500 border-b border-[#222]">
                    <th className="text-left py-1.5 px-2">名稱 / 代號</th>
                    <th className="text-right px-2">買入點</th>
                    <th className="text-right px-2">投資資金</th>
                    <th className="text-right px-2">股數</th>
                    <th className="text-left px-2">日期</th>
                    <th className="text-right px-2">今日收盤</th>
                    <th className="text-right px-2">漲跌點</th>
                    <th className="text-right px-2">盈虧金額</th>
                    <th className="px-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {activeHoldings.map((h, hIdx) => {
                    const close = quotes[h.symbol]
                    const totalPL = h.lots.reduce((acc, l) => {
                      const { money } = lotPL(l, close)
                      return money == null ? acc : acc + money
                    }, 0)
                    const plColor = totalPL > 0 ? GAIN : totalPL < 0 ? LOSS : FLAT
                    const { totalShares, totalAmount, avg } = holdingStats(h)
                    const avgPts = (avg != null && close != null) ? close - avg : null
                    const avgColor = avgPts == null ? '#888' : avgPts > 0 ? GAIN : avgPts < 0 ? LOSS : FLAT
                    const sl = stopLossPrice(avg, num(h.stopLossPct))
                    const tp = takeProfitPrice(avg, num(h.takeProfitPct))
                    const lf = lotForms[hIdx] || { date: todayStr() }
                    return (
                      <FragmentRows key={h.symbol + hIdx}>
                        {/* Holding header row — aggregate stats by 均價 */}
                        <tr className="bg-[#15171A] border-b border-[#1f1f1f]">
                          <td className="py-1.5 px-2">
                            <button
                              onClick={() => jumpHolding(h)}
                              className="text-blue-300 hover:text-blue-200 font-semibold"
                              title="查看圖表並標出均價、停損/停漲與所有買入點"
                            >
                              {h.name} <span className="text-gray-500 font-normal">{h.symbol}</span>
                            </button>
                          </td>
                          <td className="px-2 text-right font-semibold text-[#40C4FF]" title="加權平均買入點">
                            均 {avg == null ? '—' : round2(avg)}
                          </td>
                          <td className="px-2 text-right text-gray-300">{fmtMoney(totalAmount)}</td>
                          <td className="px-2 text-right text-gray-300">{totalShares || '—'}</td>
                          <td className="px-2 text-gray-500">共 {h.lots.length} 筆</td>
                          <td className="px-2 text-right text-gray-300">{close == null ? '—' : close}</td>
                          <td className="px-2 text-right font-semibold" style={{ color: avgColor }}>{fmtPts(avgPts)}</td>
                          <td className="px-2 text-right font-semibold" style={{ color: plColor }}>{fmtMoney(totalPL)}</td>
                          <td className="px-2 text-right">
                            <button onClick={() => removeHolding(hIdx)} className="text-gray-600 hover:text-red-400" title="刪除此股">🗑</button>
                          </td>
                        </tr>

                        {/* Stop-loss / take-profit settings row */}
                        <tr className="bg-[#101216] border-b border-[#222]">
                          <td className="px-2 pl-3 text-[11px] text-gray-600">停損 / 停漲</td>
                          <td colSpan={8} className="px-2 py-1">
                            <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-[11px]">
                              <span className="flex items-center gap-1" style={{ color: LOSS }}>
                                停損
                                <input
                                  type="number" value={h.stopLossPct ?? ''}
                                  onChange={e => patchHolding(hIdx, { stopLossPct: e.target.value })}
                                  onBlur={saveNow}
                                  placeholder="%" className="w-14 input text-right"
                                />
                                <span className="text-gray-500">% →</span>
                                <span>停損點 {sl == null ? '—' : sl}</span>
                              </span>
                              <span className="flex items-center gap-1" style={{ color: GAIN }}>
                                停漲
                                <input
                                  type="number" value={h.takeProfitPct ?? ''}
                                  onChange={e => patchHolding(hIdx, { takeProfitPct: e.target.value })}
                                  onBlur={saveNow}
                                  placeholder="%" className="w-14 input text-right"
                                />
                                <span className="text-gray-500">% →</span>
                                <span>停漲點 {tp == null ? '—' : tp}</span>
                              </span>
                            </div>
                          </td>
                        </tr>

                        {/* Lot rows */}
                        {h.lots.map((lot, lIdx) => {
                          const { pts, money } = lotPL(lot, close)
                          const c = pts == null ? '#888' : pts > 0 ? GAIN : pts < 0 ? LOSS : FLAT
                          return (
                            <tr key={lIdx} className="border-b border-[#1A1A1A] hover:bg-[#121212]">
                              <td className="py-1 px-2 pl-5">
                                <button
                                  onClick={() => jumpLot(h, lot)}
                                  className="text-gray-400 hover:text-blue-300"
                                  title="查看圖表並標出此買入點"
                                >
                                  ↳ {h.symbol}
                                </button>
                              </td>
                              <td className="px-2 text-right">{lot.price ?? '—'}</td>
                              <td className="px-2 text-right">{fmtMoney(lot.amount)}</td>
                              <td className="px-2 text-right">{lot.shares ?? '—'}</td>
                              <td className="px-2 text-gray-500">{lot.date || '—'}</td>
                              <td className="px-2 text-right text-gray-400">{close == null ? '—' : close}</td>
                              <td className="px-2 text-right" style={{ color: c }}>{fmtPts(pts)}</td>
                              <td className="px-2 text-right" style={{ color: c }}>{fmtMoney(money)}</td>
                              <td className="px-2 text-right">
                                <button onClick={() => removeLot(hIdx, lIdx)} className="text-gray-700 hover:text-red-400" title="刪除此筆">×</button>
                              </td>
                            </tr>
                          )
                        })}

                        {/* Add-lot row */}
                        <tr className="border-b border-[#222] bg-[#0F0F0F]">
                          <td className="py-1 px-2 pl-5 text-gray-600">+ 新增購買</td>
                          <td className="px-2"><input value={lf.price || ''} onChange={e => setLotForms(p => ({ ...p, [hIdx]: { ...lf, price: e.target.value } }))} type="number" placeholder="點" className="w-16 input" /></td>
                          <td className="px-2 text-right text-gray-500">{fmtMoney(calcAmount(num(lf.price), num(lf.shares)))}</td>
                          <td className="px-2"><input value={lf.shares || ''} onChange={e => setLotForms(p => ({ ...p, [hIdx]: { ...lf, shares: e.target.value } }))} type="number" placeholder="股" className="w-16 input" /></td>
                          <td className="px-2"><input value={lf.date || todayStr()} onChange={e => setLotForms(p => ({ ...p, [hIdx]: { ...lf, date: e.target.value } }))} type="date" className="w-32 input" /></td>
                          <td colSpan={3}></td>
                          <td className="px-2 text-right"><button onClick={() => addLot(hIdx)} className="px-2 py-0.5 rounded text-[11px] bg-blue-800 text-blue-200 hover:bg-blue-700">加入</button></td>
                        </tr>
                      </FragmentRows>
                    )
                  })}
                </tbody>
              </table>
            )}
          </>
        )}
      </div>

      <style>{`
        .input { background:#0D0D0D; border:1px solid #333; border-radius:4px; padding:4px 8px;
                 font-size:12px; color:#fff; outline:none; }
        .input:focus { border-color:#3b82f6; }
      `}</style>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] text-gray-500">{label}</span>
      {children}
    </label>
  )
}

// Render multiple <tr> from a map iteration without an extra DOM wrapper.
function FragmentRows({ children }) {
  return <>{children}</>
}
