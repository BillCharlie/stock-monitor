import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/stocks.js'

const DEFAULT_PEOPLE = ['Fiona', 'Bill', 'Yang']

// Project color convention: gains red, losses green.
const GAIN = '#EF5350'
const LOSS = '#26A69A'
const FLAT = '#FFA726'

const STATE_COLOR = {
  HEALTHY_TREND: '#40C4FF',
  OVERHEATED: '#FFA726',
  CLIMAX_TOP: '#EF5350',
  WEAKENING: '#AB47BC',
  NEUTRAL: '#888',
}
const ACTION_COLOR = { EXIT_ALL: '#EF5350', SELL_PARTIAL: '#FFA726', ADD: '#40C4FF', HOLD: '#888' }
const ACTION_LABEL = { EXIT_ALL: '全部出場', SELL_PARTIAL: '分批減倉', ADD: '加倉', HOLD: '續抱' }

const todayStr = () => new Date().toISOString().slice(0, 10)
const num = (v) => {
  const n = parseFloat(v)
  return Number.isFinite(n) ? n : null
}
const fmtMoney = (n) =>
  n == null ? '—' : n.toLocaleString('en-US', { maximumFractionDigits: 0 })
const fmtMoneySigned = (n) =>
  n == null ? '—' : (n >= 0 ? '+' : '') + n.toLocaleString('en-US', { maximumFractionDigits: 0 })
const fmtPts = (n) => (n == null ? '—' : (n >= 0 ? '+' : '') + n.toFixed(2))
// Invested amount is derived: 買入點 × 股數
const calcAmount = (price, shares) =>
  price != null && shares != null ? price * shares : null

// Aggregate a holding's buys & sells.
// - avg     : weighted-average BUY price (cost basis / strategy entry)
// - netShares: buy shares − sell shares (current position)
// - netCost : remaining invested capital at cost = avg × netShares
const holdingStats = (h) => {
  let buyShares = 0, buyAmount = 0
  for (const l of h.lots || []) {
    const sh = l.shares
    const am = l.amount != null ? l.amount : calcAmount(l.price, l.shares)
    if (sh != null) buyShares += sh
    if (am != null) buyAmount += am
  }
  const avg = buyShares > 0 ? buyAmount / buyShares : null
  let sellShares = 0, sellAmount = 0, realized = 0
  for (const s of h.sells || []) {
    const sh = s.shares
    const am = s.amount != null ? s.amount : calcAmount(s.price, s.shares)
    if (sh != null) sellShares += sh
    if (am != null) sellAmount += am
    if (sh != null && s.price != null && avg != null) realized += (s.price - avg) * sh
  }
  const hasSells = (h.sells || []).length > 0
  const netShares = buyShares - sellShares
  const netCost = avg != null ? avg * Math.max(netShares, 0) : null
  return { avg, buyShares, buyAmount, sellShares, sellAmount, realized, hasSells, netShares, netCost }
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
  const [analysis, setAnalysis] = useState({})    // symbol -> result | 'loading' | {error}
  const [expanded, setExpanded] = useState({})    // symbol -> bool (strategy panel open)

  // New-holding form (amount is derived from price × shares)
  const [form, setForm] = useState({ name: '', symbol: '', price: '', shares: '', date: todayStr() })
  // Add-lot (buy) and add-sell forms keyed by holding index
  const [lotForms, setLotForms] = useState({})
  const [sellForms, setSellForms] = useState({})

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

  const addSell = (hIdx) => {
    const sf = sellForms[hIdx] || {}
    const price = num(sf.price), shares = num(sf.shares)
    if (price == null || shares == null) { setMsg('⚠ 出倉需填賣出點與股數'); return }
    const sell = { price, shares, amount: calcAmount(price, shares), date: sf.date || todayStr() }
    const holdings = persons[activePerson].map((h, i) =>
      i === hIdx ? { ...h, sells: [...(h.sells || []), sell] } : h
    )
    persist({ ...persons, [activePerson]: holdings })
    setSellForms(prev => ({ ...prev, [hIdx]: { date: todayStr() } }))
  }

  const removeSell = (hIdx, sIdx) => {
    const holdings = persons[activePerson].map((h, i) =>
      i === hIdx ? { ...h, sells: (h.sells || []).filter((_, j) => j !== sIdx) } : h
    )
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

  const earliestDate = (h) => (h.lots.map(l => l.date).filter(Boolean).sort()[0] || '')

  // Load the position-management strategy snapshot (aggregate avg as entry).
  const loadAnalysis = async (h) => {
    const { avg } = holdingStats(h)
    if (avg == null) { setAnalysis(p => ({ ...p, [h.symbol]: { error: '缺少均價' } })); return }
    setAnalysis(p => ({ ...p, [h.symbol]: 'loading' }))
    try {
      const r = await api.getPositionAnalysis(h.symbol, round2(avg), earliestDate(h))
      setAnalysis(p => ({ ...p, [h.symbol]: r }))
    } catch (e) {
      setAnalysis(p => ({ ...p, [h.symbol]: { error: e.message } }))
    }
  }

  const toggleAnalysis = (h) => {
    const open = !expanded[h.symbol]
    setExpanded(p => ({ ...p, [h.symbol]: open }))
    if (open && analysis[h.symbol] === undefined) loadAnalysis(h)
  }

  // Build the strategy price lines. Each level carries a stable key + default
  // visibility (on); titles say how much to sell/add at that price.
  // Default-visible: 均價 + 第一段止損 + 第一目標 (not all, not none).
  const strategyLevels = (h, a) => {
    const { avg } = holdingStats(h)
    const L = a.levels || {}
    // Manual stop/take-profit the user set on the holding (merged in here).
    const msl = stopLossPrice(avg, num(h.stopLossPct))
    const mtp = takeProfitPrice(avg, num(h.takeProfitPct))
    return [
      avg != null && { key: 'avg', on: true, price: round2(avg), color: '#40C4FF', title: `均價 ${round2(avg)}`, dashed: false },
      L.stop_loss_1 != null && { key: 'sl1', on: true,  price: L.stop_loss_1, color: LOSS, title: `止損 -0.6R 減30% ${L.stop_loss_1}`, dashed: true },
      L.stop_loss_2 != null && { key: 'sl2', on: false, price: L.stop_loss_2, color: LOSS, title: `止損 -1.0R 減40% ${L.stop_loss_2}`, dashed: true },
      L.stop_loss_3 != null && { key: 'sl3', on: false, price: L.stop_loss_3, color: LOSS, title: `止損 -1.5R 清倉 ${L.stop_loss_3}`, dashed: true },
      L.trailing_stop != null && { key: 'trail', on: false, price: L.trailing_stop, color: '#FFA726', title: `移動止損 ${L.trailing_stop}`, dashed: true },
      L.target_1R != null && { key: 'tp1', on: true,  price: L.target_1R, color: GAIN, title: `目標 +1R 停利 ${L.target_1R}`, dashed: true },
      L.target_2R != null && { key: 'tp2', on: false, price: L.target_2R, color: GAIN, title: `目標 +2R 停利 ${L.target_2R}`, dashed: true },
      L.target_3R != null && { key: 'tp3', on: false, price: L.target_3R, color: GAIN, title: `目標 +3R 停利 ${L.target_3R}`, dashed: true },
      msl != null && { key: 'msl', on: false, price: msl, color: '#80CBC4', title: `自訂停損 ${msl}`, dashed: true },
      mtp != null && { key: 'mtp', on: false, price: mtp, color: '#FF8A80', title: `自訂停利 ${mtp}`, dashed: true },
      ...dailyLevels(a),
    ].filter(Boolean)
  }

  // 明日(T+1)時機關鍵價位（今高/今低/MA5/MA10/前高/平台支撐），預設關閉，需要時勾選。
  const dailyLevels = (a) => {
    const D = (a && a.daily && a.daily.levels) || {}
    return [
      D.today_high != null && { key: 'dth', on: false, price: D.today_high, color: '#B0BEC5', title: `今日高 ${D.today_high}`, dashed: true },
      D.today_low != null && { key: 'dtl', on: false, price: D.today_low, color: '#B0BEC5', title: `今日低 ${D.today_low}`, dashed: true },
      D.ma5 != null && { key: 'dma5', on: false, price: D.ma5, color: '#FF6D00', title: `MA5 ${D.ma5}`, dashed: true },
      D.ma10 != null && { key: 'dma10', on: false, price: D.ma10, color: '#FFD600', title: `MA10 ${D.ma10}`, dashed: true },
      D.prev_high != null && { key: 'dph', on: false, price: D.prev_high, color: '#EF5350', title: `前高 ${D.prev_high}`, dashed: true },
      D.platform_support != null && { key: 'dps', on: false, price: D.platform_support, color: '#26A69A', title: `平台支撐 ${D.platform_support}`, dashed: true },
    ].filter(Boolean)
  }

  // The single entry point: open the chart with all strategy lines + buy points.
  const jumpStrategy = (h, a) => {
    const marks = h.lots.filter(l => l.price != null).map(l => ({ time: l.date, price: l.price, label: l.date }))
    onJumpToChart?.(h.symbol, h.name, marks, strategyLevels(h, a))
  }

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
                    const { avg, netShares, netCost, realized, hasSells } = holdingStats(h)
                    // Unrealized P/L on the remaining (net) position, by average cost.
                    const unrealPL = (avg != null && close != null) ? (close - avg) * Math.max(netShares, 0) : null
                    const realColor = realized > 0 ? GAIN : realized < 0 ? LOSS : FLAT
                    const unrealColor = unrealPL == null ? '#888' : unrealPL > 0 ? GAIN : unrealPL < 0 ? LOSS : FLAT
                    const avgPts = (avg != null && close != null) ? close - avg : null
                    const avgColor = avgPts == null ? '#888' : avgPts > 0 ? GAIN : avgPts < 0 ? LOSS : FLAT
                    const sl = stopLossPrice(avg, num(h.stopLossPct))
                    const tp = takeProfitPrice(avg, num(h.takeProfitPct))
                    const lf = lotForms[hIdx] || { date: todayStr() }
                    const sfm = sellForms[hIdx] || { date: todayStr() }
                    return (
                      <FragmentRows key={h.symbol + hIdx}>
                        {/* Holding header row — aggregate stats by 均價 */}
                        <tr className="bg-[#15171A] border-b border-[#1f1f1f]">
                          <td className="py-1.5 px-2">
                            <span className="text-gray-200 font-semibold">
                              {h.name} <span className="text-gray-500 font-normal">{h.symbol}</span>
                            </span>
                          </td>
                          <td className="px-2 text-right font-semibold text-[#40C4FF]" title="加權平均買入點">
                            均 {avg == null ? '—' : round2(avg)}
                          </td>
                          <td className="px-2 text-right text-gray-300" title="淨投資成本 = 均價 × 淨持股">{fmtMoney(netCost)}</td>
                          <td className="px-2 text-right text-gray-300" title="淨持股 = 買入 − 賣出">{netShares || '—'}</td>
                          <td className="px-2 text-gray-500">買{h.lots.length} 賣{(h.sells || []).length}</td>
                          <td className="px-2 text-right text-gray-300">{close == null ? '—' : close}</td>
                          <td className="px-2 text-right font-semibold" style={{ color: avgColor }}>{fmtPts(avgPts)}</td>
                          <td className="px-2 text-right font-semibold">
                            {hasSells ? (
                              <div className="flex flex-col leading-tight">
                                <span style={{ color: realColor }} title="已實現（出倉）盈虧">已實 {fmtMoneySigned(realized)}</span>
                                <span style={{ color: unrealColor }} title="未實現（剩餘持倉）盈虧">浮動 {unrealPL == null ? '—' : fmtMoneySigned(unrealPL)}</span>
                              </div>
                            ) : (
                              <span style={{ color: unrealColor }}>{unrealPL == null ? '—' : fmtMoneySigned(unrealPL)}</span>
                            )}
                          </td>
                          <td className="px-2 text-right whitespace-nowrap">
                            <button
                              onClick={() => toggleAnalysis(h)}
                              className={`mr-2 text-[11px] ${expanded[h.symbol] ? 'text-blue-300' : 'text-gray-500 hover:text-blue-300'}`}
                              title="倉位管理策略分析（依此股彙總均價計算）"
                            >
                              {expanded[h.symbol] ? '▾分析' : '▸分析'}
                            </button>
                            <button onClick={() => removeHolding(hIdx)} className="text-gray-600 hover:text-red-400" title="刪除此股">🗑</button>
                          </td>
                        </tr>

                        {/* Strategy analysis row */}
                        {expanded[h.symbol] && (
                          <tr className="bg-[#0B0E12] border-b border-[#222]">
                            <td colSpan={9} className="px-3 py-2">
                              <AnalysisBlock a={analysis[h.symbol]} onMark={(res) => jumpStrategy(h, res)} onReload={() => loadAnalysis(h)} />
                            </td>
                          </tr>
                        )}

                        {/* Custom (user-defined) stop-loss / take-profit settings row */}
                        <tr className="bg-[#101216] border-b border-[#222]">
                          <td className="px-2 pl-3 text-[11px] text-gray-600">自訂停損 / 自訂停利</td>
                          <td colSpan={8} className="px-2 py-1">
                            <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-[11px]">
                              <span className="flex items-center gap-1" style={{ color: LOSS }}>
                                自訂停損
                                <input
                                  type="number" value={h.stopLossPct ?? ''}
                                  onChange={e => patchHolding(hIdx, { stopLossPct: e.target.value })}
                                  onBlur={saveNow}
                                  placeholder="%" className="w-14 input text-right"
                                />
                                <span className="text-gray-500">% →</span>
                                <span>自訂停損點 {sl == null ? '—' : sl}</span>
                              </span>
                              <span className="flex items-center gap-1" style={{ color: GAIN }}>
                                自訂停利
                                <input
                                  type="number" value={h.takeProfitPct ?? ''}
                                  onChange={e => patchHolding(hIdx, { takeProfitPct: e.target.value })}
                                  onBlur={saveNow}
                                  placeholder="%" className="w-14 input text-right"
                                />
                                <span className="text-gray-500">% →</span>
                                <span>自訂停利點 {tp == null ? '—' : tp}</span>
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

                        {/* Sell records — realized P/L = (賣出點 − 均價) × 股數 */}
                        {(h.sells || []).map((sell, sIdx) => {
                          const rPts = (sell.price != null && avg != null) ? sell.price - avg : null
                          const rMoney = (rPts != null && sell.shares != null) ? rPts * sell.shares : null
                          const rc = rPts == null ? '#888' : rPts > 0 ? GAIN : rPts < 0 ? LOSS : FLAT
                          return (
                            <tr key={'s' + sIdx} className="border-b border-[#1A1A1A] bg-[#120e0e]">
                              <td className="py-1 px-2 pl-5 text-[#FF8A80]">↑ 出倉</td>
                              <td className="px-2 text-right">{sell.price ?? '—'}</td>
                              <td className="px-2 text-right">{fmtMoney(sell.amount)}</td>
                              <td className="px-2 text-right">−{sell.shares ?? '—'}</td>
                              <td className="px-2 text-gray-500">{sell.date || '—'}</td>
                              <td className="px-2 text-right text-gray-600">已實現</td>
                              <td className="px-2 text-right" style={{ color: rc }}>{fmtPts(rPts)}</td>
                              <td className="px-2 text-right" style={{ color: rc }}>{fmtMoney(rMoney)}</td>
                              <td className="px-2 text-right">
                                <button onClick={() => removeSell(hIdx, sIdx)} className="text-gray-700 hover:text-red-400" title="刪除此出倉">×</button>
                              </td>
                            </tr>
                          )
                        })}

                        {/* Add-sell row */}
                        <tr className="border-b border-[#222] bg-[#0F0B0B]">
                          <td className="py-1 px-2 pl-5 text-[#FF8A80]">+ 新增出倉</td>
                          <td className="px-2"><input value={sfm.price || ''} onChange={e => setSellForms(p => ({ ...p, [hIdx]: { ...sfm, price: e.target.value } }))} type="number" placeholder="賣出點" className="w-16 input" /></td>
                          <td className="px-2 text-right text-gray-500">{fmtMoney(calcAmount(num(sfm.price), num(sfm.shares)))}</td>
                          <td className="px-2"><input value={sfm.shares || ''} onChange={e => setSellForms(p => ({ ...p, [hIdx]: { ...sfm, shares: e.target.value } }))} type="number" placeholder="股" className="w-16 input" /></td>
                          <td className="px-2"><input value={sfm.date || todayStr()} onChange={e => setSellForms(p => ({ ...p, [hIdx]: { ...sfm, date: e.target.value } }))} type="date" className="w-32 input" /></td>
                          <td colSpan={3}></td>
                          <td className="px-2 text-right"><button onClick={() => addSell(hIdx)} className="px-2 py-0.5 rounded text-[11px] bg-[#8a3b3b] text-red-100 hover:bg-[#a04848]">出倉</button></td>
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

// Position-management strategy snapshot (computed from the holding's avg price).
function AnalysisBlock({ a, onMark, onReload }) {
  if (a === undefined || a === 'loading') {
    return <div className="text-xs text-gray-500">分析中...</div>
  }
  if (a?.error) {
    const tip = a.error === 'INSUFFICIENT_DATA' ? '歷史資料不足（需 ≥60 日）' : a.error
    return (
      <div className="text-xs text-yellow-400">
        無法分析：{tip}
        <button onClick={onReload} className="ml-2 text-blue-300 hover:text-blue-200">重試</button>
      </div>
    )
  }
  const ind = a.indicators || {}
  const stat = (label, val) => (
    <span className="text-gray-400">{label} <span className="text-gray-200">{val}</span></span>
  )
  const dec = a.decision || {}
  const ratioTxt = dec.ratio ? `（${dec.ratio_type === 'add' ? '加倉' : '減倉'} ${Math.round(dec.ratio * 100)}%）` : ''
  return (
    <div className="text-[11px] space-y-1.5">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="px-2 py-0.5 rounded text-white font-semibold" style={{ background: STATE_COLOR[a.state] || '#888' }}>
          {a.state_label}
        </span>
        <span className="px-2 py-0.5 rounded font-semibold" style={{ color: ACTION_COLOR[dec.action] || '#888', border: `1px solid ${ACTION_COLOR[dec.action] || '#888'}` }}>
          {ACTION_LABEL[dec.action] || dec.action} {ratioTxt}
        </span>
        <span className="text-gray-400">{dec.reason}</span>
        {a.high_volatility && <span className="text-yellow-400">⚠ 高波動，建議降低部位</span>}
        <button onClick={() => onMark(a)} className="ml-auto px-2 py-0.5 rounded bg-blue-800 text-blue-200 hover:bg-blue-700">在K線圖標出策略價位</button>
      </div>
      <div className="flex gap-x-4 gap-y-1 flex-wrap">
        {stat('均價(進場)', a.entry_price)}
        {stat('收盤', a.close)}
        {stat('損益%', (a.pnl_pct >= 0 ? '+' : '') + a.pnl_pct + '%')}
        {stat('profit_R', a.profit_R)}
        {stat('ATR%', a.atr_pct + '%')}
        {stat('基礎止損', a.base_stop_pct + '%')}
        {stat('RSI', ind.rsi ?? '—')}
        {stat('量比', ind.volume_ratio ?? '—')}
        {stat('距MA20', ind.ma20 != null ? (((a.close / ind.ma20 - 1) * 100).toFixed(1) + '%') : '—')}
        {stat('回撤', ind.drawdown_from_peak_pct != null ? ind.drawdown_from_peak_pct + '%' : '—')}
      </div>
      <div className="flex gap-x-4 gap-y-1 flex-wrap">
        <span style={{ color: LOSS }}>止損 -0.6R/-1.0R/-1.5R: {a.levels.stop_loss_1} / {a.levels.stop_loss_2} / {a.levels.stop_loss_3}</span>
        {a.levels.trailing_stop != null && <span style={{ color: '#FFA726' }}>移動止損: {a.levels.trailing_stop}</span>}
        <span style={{ color: GAIN }}>目標 +1R/+2R/+3R: {a.levels.target_1R} / {a.levels.target_2R} / {a.levels.target_3R}</span>
      </div>

      {a.daily && <DailyBlock d={a.daily} />}
    </div>
  )
}

// 明日(T+1) 短線買賣時機建議 — K 線型態 + 量價 + 明日條件式觸發。
function DailyBlock({ d }) {
  const sc = d.score || {}
  const totalColor = sc.total >= 4 ? GAIN : sc.total <= -2 ? LOSS : FLAT
  return (
    <div className="mt-1 pt-1.5 border-t border-[#1f1f1f] space-y-1 text-[10px] leading-tight">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-gray-500" title="T+1＝以今日收盤為基準的下一個交易日">明日時機(T+1)</span>
        <span className="px-1.5 py-0.5 rounded bg-[#1A2330] text-gray-200">{d.candle_type}</span>
        <span className="text-gray-400">位置 {d.position}</span>
        <span className="font-semibold" style={{ color: totalColor }}>打分 {sc.total}（{d.bias}）</span>
        <span className="text-gray-600">趨{sc.trend} K{sc.kline} 量{sc.volume} 位{sc.position}</span>
      </div>
      <div className="grid grid-cols-2 gap-x-3">
        <div className="flex flex-col gap-0.5">
          <span style={{ color: GAIN }} className="font-semibold">明日偏多觸發</span>
          {(d.long_triggers || []).map((t, i) => (
            <span key={i} style={{ color: GAIN }} className="pl-1.5">（情況{i + 1}）{t}</span>
          ))}
        </div>
        <div className="flex flex-col gap-0.5">
          <span style={{ color: LOSS }} className="font-semibold">明日偏空觸發</span>
          {(d.short_triggers || []).map((t, i) => (
            <span key={i} style={{ color: LOSS }} className="pl-1.5">（情況{i + 1}）{t}</span>
          ))}
        </div>
      </div>
      <div className="text-gray-300">建議買法：{d.buy_method}</div>
    </div>
  )
}
