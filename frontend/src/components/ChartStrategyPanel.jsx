import { useEffect, useState } from 'react'
import { api } from '../api/stocks.js'

// Project color convention: gains red, losses green.
const GAIN = '#EF5350'
const LOSS = '#26A69A'
const FLAT = '#FFA726'

// Chart view shows next-day TIMING only — mark the trigger price levels.
function buildLevels(a) {
  const D = (a.daily && a.daily.levels) || {}
  return [
    D.today_high != null && { key: 'dth', on: true, price: D.today_high, color: '#B0BEC5', title: `今日高 ${D.today_high}`, dashed: true },
    D.today_low != null && { key: 'dtl', on: true, price: D.today_low, color: '#B0BEC5', title: `今日低 ${D.today_low}`, dashed: true },
    D.ma5 != null && { key: 'dma5', on: true, price: D.ma5, color: '#FF6D00', title: `MA5 ${D.ma5}`, dashed: true },
    D.ma10 != null && { key: 'dma10', on: false, price: D.ma10, color: '#FFD600', title: `MA10 ${D.ma10}`, dashed: true },
    D.prev_high != null && { key: 'dph', on: false, price: D.prev_high, color: '#EF5350', title: `前高 ${D.prev_high}`, dashed: true },
    D.platform_support != null && { key: 'dps', on: false, price: D.platform_support, color: '#26A69A', title: `平台支撐 ${D.platform_support}`, dashed: true },
  ].filter(Boolean)
}

// Strategy + next-day timing analysis for the currently charted symbol.
// Entry-free: uses latest close as an assumed entry, so it works for any stock.
export default function ChartStrategyPanel({ symbol, name, onMark }) {
  const [open, setOpen] = useState(false)
  const [a, setA] = useState(null)   // result | 'loading' | {error}

  useEffect(() => {
    if (!open || !symbol) return
    setA('loading')
    let cancelled = false
    api.getPositionAnalysis(symbol)
      .then(r => { if (!cancelled) setA(r) })
      .catch(e => { if (!cancelled) setA({ error: e.message }) })
    return () => { cancelled = true }
  }, [open, symbol])

  const daily = (a && a.daily) || null
  const sc = (daily && daily.score) || {}

  return (
    <div className="border-b border-[#2A2A2A] bg-[#0A0A0A] flex-shrink-0">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-[#141414]"
      >
        <span className="text-[11px] text-blue-300">{open ? '▾' : '▸'} 次日買賣時機</span>
        <span className="text-[10px] text-gray-600">{name} {symbol}</span>
      </button>

      {open && (
        <div className="px-3 pb-2 text-[11px]">
          {a === 'loading' && <div className="text-gray-500">分析中...</div>}
          {a && a.error && (
            <div className="text-yellow-400">
              無法分析：{a.error === 'INSUFFICIENT_DATA' ? '歷史資料不足（需 ≥60 日）' : a.error}
            </div>
          )}
          {a && !a.error && a !== 'loading' && !daily && (
            <div className="text-gray-500">本標的暫無次日時機資料</div>
          )}
          {daily && (
            <div className="space-y-1">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="px-1.5 py-0.5 rounded bg-[#1A2330] text-gray-200">{daily.candle_type}</span>
                <span className="text-gray-400">位置 {daily.position}</span>
                <span className="font-semibold" style={{ color: sc.total >= 4 ? GAIN : sc.total <= -2 ? LOSS : FLAT }}>打分 {sc.total}（{daily.bias}）</span>
                <span className="text-gray-600">趨{sc.trend} K{sc.kline} 量{sc.volume} 位{sc.position}</span>
                <button onClick={() => onMark?.([], buildLevels(a))} className="ml-auto px-2 py-0.5 rounded bg-blue-800 text-blue-200 hover:bg-blue-700">標出時機價位</button>
              </div>
              <div className="flex flex-col gap-0.5">
                <span style={{ color: GAIN }}>偏多觸發：{(daily.long_triggers || []).join('；')}</span>
                <span style={{ color: LOSS }}>偏空觸發：{(daily.short_triggers || []).join('；')}</span>
              </div>
              <div className="text-gray-300">建議買法：{daily.buy_method}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
