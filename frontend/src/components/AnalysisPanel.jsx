import { useEffect, useState } from 'react'
import { api } from '../api/stocks.js'

function SignalRow({ s }) {
  const cls = s.type === 'bullish' ? 'signal-bullish' : s.type === 'bearish' ? 'signal-bearish' : 'signal-neutral'
  const icon = s.type === 'bullish' ? '▲' : s.type === 'bearish' ? '▼' : '─'
  return (
    <div className="flex items-start gap-2 py-0.5">
      <span className={`text-[10px] flex-shrink-0 mt-0.5 ${cls}`}>{icon}</span>
      <div>
        <span className="text-[10px] text-gray-500">[{s.indicator}] </span>
        <span className={`text-xs ${cls}`}>{s.signal}</span>
      </div>
    </div>
  )
}

function IndicatorGrid({ indicators }) {
  const items = [
    { label: 'MA5',    val: indicators?.MA5 },
    { label: 'MA10',   val: indicators?.MA10 },
    { label: 'MA20',   val: indicators?.MA20 },
    { label: 'MA60',   val: indicators?.MA60 },
    { label: 'MA120',  val: indicators?.MA120 },
    { label: 'MA240',  val: indicators?.MA240 },
    { label: 'RSI(14)',val: indicators?.RSI },
    { label: 'K',      val: indicators?.K },
    { label: 'D',      val: indicators?.D },
    { label: 'BB上軌', val: indicators?.BB_upper },
    { label: 'BB中軌', val: indicators?.BB_middle },
    { label: 'BB下軌', val: indicators?.BB_lower },
  ]
  return (
    <div className="grid grid-cols-3 gap-1 mt-2">
      {items.map(({ label, val }) => (
        <div key={label} className="bg-[#1A1A1A] rounded px-2 py-1 flex justify-between items-center">
          <span className="text-[10px] text-gray-500">{label}</span>
          <span className="text-xs text-gray-200 font-mono">{val != null ? val.toLocaleString() : '—'}</span>
        </div>
      ))}
    </div>
  )
}

function PredictionCard({ pred, label }) {
  if (!pred) return null
  const isUp = pred.pred_change_pct >= 0
  return (
    <div className="bg-[#0A1A0A] border border-[#1A3A1A] rounded p-3 mt-2">
      <div className="text-xs text-gray-400 mb-1">{label} ({pred.method})</div>
      <div className="flex items-baseline gap-3">
        <span className="text-lg font-mono text-white">{pred.pred_price?.toLocaleString()}</span>
        <span className={`text-sm font-mono ${isUp ? 'text-[#26A69A]' : 'text-[#EF5350]'}`}>
          {isUp ? '+' : ''}{pred.pred_change_pct?.toFixed(2)}%
        </span>
      </div>
      <div className="text-[10px] text-gray-600 mt-1">
        95% CI: [{pred.confidence_interval?.[0]?.toLocaleString()} – {pred.confidence_interval?.[1]?.toLocaleString()}]
        &nbsp;|&nbsp; R² = {pred.r_squared}
        &nbsp;|&nbsp; 趨勢: {pred.trend}
      </div>
    </div>
  )
}

function SingleAnalysis({ symbol, stockName }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!symbol) return
    setLoading(true)
    setError(null)
    api.getAnalysis(symbol, stockName)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [symbol, stockName])

  if (loading) return <div className="p-4 text-gray-400 text-sm">分析中...</div>
  if (error) return <div className="p-4 text-red-400 text-sm">{error}</div>
  if (!data) return null
  if (data.error) return <div className="p-4 text-yellow-400 text-sm">{data.error}</div>

  const isUp = data.daily_change_pct >= 0

  return (
    <div className="p-4 space-y-3 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <span className="text-xl font-bold text-white">{data.name}</span>
          <span className="text-gray-500 ml-2 text-sm">{data.symbol}</span>
        </div>
        <div className="flex items-baseline gap-3">
          <span className="text-2xl font-mono text-white">{data.price?.toLocaleString()}</span>
          <span className={`text-base font-mono ${isUp ? 'text-[#26A69A]' : 'text-[#EF5350]'}`}>
            {isUp ? '+' : ''}{data.daily_change_pct?.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* Rating */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-gray-400">綜合評級</span>
        <span className={`text-base font-bold rating-${data.rating_key}`}>{data.rating}</span>
        <span className="text-xs text-gray-600">評分: {data.score?.toFixed(1)}</span>
      </div>

      {/* Support / Resistance */}
      {(data.support || data.resistance) && (
        <div className="flex gap-4 text-xs">
          {data.support && (
            <span className="text-gray-400">支撐位: <span className="text-[#26A69A] font-mono">{data.support?.toLocaleString()}</span></span>
          )}
          {data.resistance && (
            <span className="text-gray-400">壓力位: <span className="text-[#EF5350] font-mono">{data.resistance?.toLocaleString()}</span></span>
          )}
        </div>
      )}

      {/* Technical indicators grid */}
      <IndicatorGrid indicators={data.indicators} />

      {/* Signals */}
      <div>
        <div className="text-xs text-gray-400 mb-1 font-semibold">技術信號</div>
        <div className="bg-[#111] rounded p-2 space-y-0.5 max-h-48 overflow-y-auto">
          {data.signals?.map((s, i) => <SignalRow key={i} s={s} />)}
        </div>
      </div>

      {/* Predictions */}
      <div>
        <div className="text-xs text-gray-400 mb-1 font-semibold">量化預測（基於歷史數學模型，僅供參考）</div>
        <PredictionCard pred={data.prediction_5d} label="5日預測" />
        <PredictionCard pred={data.prediction_20d} label="20日預測" />
      </div>

      <div className="text-[10px] text-gray-700 pt-2">
        ⚠ 以上分析基於技術指標數學模型，不構成投資建議。投資有風險，請自行判斷。
        最後更新: {data.generated_at}
      </div>
    </div>
  )
}

function DailyReport() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = () => {
    setLoading(true)
    api.getDailyReport()
      .then(setReport)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return <div className="p-4 text-gray-400">載入報告中...</div>
  if (error) return (
    <div className="p-4">
      <div className="text-yellow-400 text-sm mb-2">{error}</div>
      <div className="text-gray-500 text-xs">請點擊右上角「生成每日報告」按鈕以產生當日分析。</div>
    </div>
  )
  if (!report) return null

  return (
    <div className="p-4 overflow-y-auto h-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-bold text-white">每日投資分析報告</div>
          <div className="text-xs text-gray-500">{report.date} | 生成: {report.generated_at}</div>
        </div>
        <div className={`px-3 py-1 rounded text-sm font-semibold ${
          report.market_sentiment === '多頭' ? 'bg-[#0A2A0A] text-[#26A69A]' :
          report.market_sentiment === '空頭' ? 'bg-[#2A0A0A] text-[#EF5350]' :
          'bg-[#1A1A0A] text-[#FFA726]'
        }`}>
          市場情緒: {report.market_sentiment}
        </div>
      </div>

      {/* Top Opportunities */}
      {report.top_opportunities?.length > 0 && (
        <div>
          <div className="text-sm font-semibold text-[#26A69A] mb-2">買入機會 TOP 5</div>
          <div className="space-y-1">
            {report.top_opportunities.map((s, i) => (
              <div key={s.symbol} className="flex items-center justify-between bg-[#0A1A0A] rounded px-3 py-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-gray-600">#{i+1}</span>
                  <span className="text-xs text-white">{s.name}</span>
                  <span className="text-[10px] text-gray-500">{s.symbol}</span>
                </div>
                <span className={`text-xs font-bold rating-${s.rating?.includes('強力') && s.score > 0 ? 'strong_buy' : 'buy'}`}>{s.rating}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Risks */}
      {report.top_risks?.length > 0 && (
        <div>
          <div className="text-sm font-semibold text-[#EF5350] mb-2">風險警示 TOP 5</div>
          <div className="space-y-1">
            {report.top_risks.map((s, i) => (
              <div key={s.symbol} className="flex items-center justify-between bg-[#1A0A0A] rounded px-3 py-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-gray-600">#{i+1}</span>
                  <span className="text-xs text-white">{s.name}</span>
                  <span className="text-[10px] text-gray-500">{s.symbol}</span>
                </div>
                <span className="text-xs font-bold rating-sell">{s.rating}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sector Summary */}
      <div>
        <div className="text-sm font-semibold text-gray-300 mb-2">板塊情緒總覽</div>
        <div className="grid grid-cols-2 gap-1.5">
          {Object.entries(report.sector_summary || {}).map(([sector, info]) => (
            <div key={sector} className="bg-[#141414] rounded px-2 py-1.5 flex items-center justify-between">
              <span className="text-[10px] text-gray-400 truncate">{sector}</span>
              <span className={`text-[10px] font-semibold ml-2 flex-shrink-0 ${
                info.sentiment === '多頭' ? 'text-[#26A69A]' :
                info.sentiment === '空頭' ? 'text-[#EF5350]' : 'text-[#FFA726]'
              }`}>
                {info.sentiment} ({info.avg_score > 0 ? '+' : ''}{info.avg_score})
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* All stock summaries */}
      {report.all_results && (
        <div>
          <div className="text-sm font-semibold text-gray-300 mb-2">個股摘要</div>
          <div className="space-y-0.5 max-h-96 overflow-y-auto">
            {Object.values(report.all_results).sort((a, b) => b.score - a.score).map(r => (
              <div key={r.symbol} className="flex items-center justify-between px-2 py-1 rounded hover:bg-[#1A1A1A]">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-white w-16 truncate">{r.name}</span>
                  <span className="text-[10px] text-gray-600 w-20">{r.symbol}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-[10px] ${r.daily_change_pct >= 0 ? 'text-[#26A69A]' : 'text-[#EF5350]'}`}>
                    {r.daily_change_pct >= 0 ? '+' : ''}{r.daily_change_pct?.toFixed(2)}%
                  </span>
                  <span className={`text-[10px] font-semibold rating-${r.rating_key}`}>{r.rating}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-[10px] text-gray-700 pt-2">
        ⚠ 本報告完全基於技術指標數學模型自動生成，不構成任何投資建議。
        過去表現不代表未來結果，投資前請做好充分研究與風險評估。
      </div>
    </div>
  )
}

export default function AnalysisPanel({ symbol, stockName, mode }) {
  if (mode === 'report') return <DailyReport />
  return <SingleAnalysis symbol={symbol} stockName={stockName} />
}
