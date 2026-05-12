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
        <span className={`text-sm font-mono ${isUp ? 'text-[#EF5350]' : 'text-[#26A69A]'}`}>
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

function TrumpNewsReportSummary({ data }) {
  if (!data?.impact && !data?.sections) return null
  const impact = data.impact || {}
  const themes = impact.themes || []
  const sectors = impact.sectors || []
  const sections = data.sections || {}
  const latest = [
    ...(sections.truth_posts || []).slice(0, 2),
    ...(sections.white_house || []).slice(0, 2),
    ...(sections.english_news || []).slice(0, 2),
    ...(sections.x_posts || []).slice(0, 1),
  ].slice(0, 7)

  return (
    <div>
      <div className="text-sm font-semibold text-[#40C4FF] mb-2">TrumpNews 政策訊號</div>
      <div className="bg-[#101214] border border-[#1E2833] rounded p-3 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] text-gray-500">整體判讀</span>
          <span className="text-xs text-gray-200">{impact.overall || '目前未偵測到明確市場板塊衝擊訊號'}</span>
        </div>

        {themes.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
            {themes.slice(0, 4).map(theme => (
              <div key={theme.id} className="bg-[#0A0D10] rounded px-2 py-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] text-white truncate">{theme.label}</span>
                  <span className="text-[9px] text-[#FFA726] flex-shrink-0">{theme.bias}</span>
                </div>
                <div className="text-[9px] text-gray-500 mt-1">{(theme.sectors || []).slice(0, 4).join('、')}</div>
              </div>
            ))}
          </div>
        )}

        {sectors.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {sectors.slice(0, 8).map(s => (
              <span key={s.sector} className="text-[8px] px-1 rounded bg-[#172018] text-[#8BC34A]">
                {s.sector}
              </span>
            ))}
          </div>
        )}

        {latest.length > 0 && (
          <div className="space-y-1 pt-1 border-t border-[#1A1A1A]">
            {latest.map(item => (
              <a key={item.id || item.link} href={item.link} target="_blank" rel="noreferrer noopener"
                className="flex items-start gap-2 text-[10px] hover:bg-[#151515] rounded px-1 py-0.5">
                <span className="text-[#40C4FF] flex-shrink-0 w-20 truncate">{item.source}</span>
                <span className="text-gray-400 line-clamp-1">{item.title || item.summary}</span>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── TW: 三大法人 panel ────────────────────────────────────────────────────────
function InvestorsTW({ data }) {
  const trend = data.trend || []
  const foreignVals = trend.map(d => d.foreign_net)
  const maxAbs = Math.max(...foreignVals.map(Math.abs), 1)

  const fmt = v => {
    if (v == null) return '—'
    const abs = Math.abs(v)
    const sign = v >= 0 ? '+' : '-'
    if (abs >= 10000) return `${sign}${(abs / 10000).toFixed(1)}萬`
    return `${sign}${abs.toLocaleString()}`
  }

  return (
    <div className="space-y-3 pt-1">
      {/* 三大法人最新數字 */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: '外資買賣超', val: data.foreign_net, color: '#40C4FF' },
          { label: '投信買賣超', val: data.trust_net,   color: '#AB47BC' },
          { label: '自營商買賣超', val: data.dealer_net, color: '#FFA726' },
        ].map(({ label, val, color }) => (
          <div key={label} className="bg-[#111] rounded p-2 text-center border border-[#1E1E1E]">
            <div className="text-[9px] text-gray-600 mb-1">{label}</div>
            <div className={`text-sm font-mono font-bold ${val >= 0 ? 'text-[#EF5350]' : 'text-[#26A69A]'}`}>
              {fmt(val)}
            </div>
            <div className="text-[9px] text-gray-700">張</div>
          </div>
        ))}
      </div>

      {/* 外資買賣超趨勢小圖 */}
      {trend.length > 1 && (
        <div>
          <div className="text-[9px] text-gray-600 mb-1">外資近{trend.length}日買賣超 (張)</div>
          <div className="flex items-stretch gap-0.5 h-16 bg-[#0A0A0A] rounded p-1">
            {trend.map((d, i) => {
              const pct = Math.abs(d.foreign_net) / maxAbs
              const isPos = d.foreign_net >= 0
              return (
                <div key={i} className="flex-1 flex flex-col items-center justify-center gap-0"
                  title={`${d.date}: ${d.foreign_net?.toLocaleString()}張`}>
                  <div className="w-full flex-1 flex items-end justify-center">
                    {isPos && (
                      <div className="w-full rounded-sm"
                        style={{ height: `${pct * 100}%`, minHeight: 2, background: '#EF5350' }} />
                    )}
                  </div>
                  <div className="w-full flex-1 flex items-start justify-center">
                    {!isPos && (
                      <div className="w-full rounded-sm"
                        style={{ height: `${pct * 100}%`, minHeight: 2, background: '#26A69A' }} />
                    )}
                  </div>
                </div>
              )
            })}
          </div>
          <div className="flex justify-between text-[8px] text-gray-700 mt-0.5">
            <span>{trend[0]?.date?.slice(5)}</span>
            <span>{trend[trend.length - 1]?.date?.slice(5)}</span>
          </div>
        </div>
      )}

      {/* 三大法人合計 */}
      <div className="flex items-center justify-between text-[10px] bg-[#111] rounded px-3 py-1.5 border border-[#1E1E1E]">
        <span className="text-gray-500">三大法人合計買賣超</span>
        <span className={`font-mono font-bold ${data.total_net >= 0 ? 'text-[#EF5350]' : 'text-[#26A69A]'}`}>
          {fmt(data.total_net)} 張
        </span>
        <span className="text-gray-700 text-[9px]">{data.latest_date}</span>
      </div>
    </div>
  )
}

// ── US: Institutional breakdown panel ─────────────────────────────────────────
function InvestorsUS({ data }) {
  const insidersPct  = data.held_pct_insiders     != null ? (data.held_pct_insiders * 100).toFixed(1) : null
  const instPct      = data.held_pct_institutions != null ? (data.held_pct_institutions * 100).toFixed(1) : null
  const retailPct    = insidersPct && instPct
    ? Math.max(0, 100 - parseFloat(insidersPct) - parseFloat(instPct)).toFixed(1)
    : null

  const barWidth = (pct) => pct != null ? `${Math.min(100, parseFloat(pct))}%` : '0%'

  return (
    <div className="space-y-3 pt-1">
      {/* Stacked ownership bar */}
      {(insidersPct || instPct) && (
        <div>
          <div className="text-[9px] text-gray-600 mb-1">持股結構</div>
          <div className="flex h-3 rounded overflow-hidden gap-px">
            {instPct && (
              <div title={`機構 ${instPct}%`}
                style={{ width: barWidth(instPct), background: '#40C4FF' }} />
            )}
            {insidersPct && (
              <div title={`內部人 ${insidersPct}%`}
                style={{ width: barWidth(insidersPct), background: '#FFA726' }} />
            )}
            {retailPct && (
              <div title={`散戶 ${retailPct}%`}
                style={{ flex: 1, background: '#2A2A2A' }} />
            )}
          </div>
          <div className="flex gap-3 mt-1.5 text-[9px]">
            {instPct && <span><span className="inline-block w-2 h-2 rounded-sm mr-1" style={{background:'#40C4FF'}} />機構 {instPct}%</span>}
            {insidersPct && <span><span className="inline-block w-2 h-2 rounded-sm mr-1" style={{background:'#FFA726'}} />內部人 {insidersPct}%</span>}
            {retailPct && <span><span className="inline-block w-2 h-2 rounded-sm mr-1" style={{background:'#2A2A2A', border:'1px solid #444'}} />散戶 ≈{retailPct}%</span>}
          </div>
        </div>
      )}

      {/* Top institutions */}
      {data.top_institutions?.length > 0 && (
        <div>
          <div className="text-[9px] text-gray-600 mb-1">前{data.top_institutions.length}大機構持股</div>
          <div className="space-y-px max-h-44 overflow-y-auto">
            {data.top_institutions.map((inst, i) => (
              <div key={i} className="flex items-center justify-between px-2 py-1 bg-[#111] rounded text-[10px]">
                <span className="text-gray-400 truncate flex-1 mr-2">{inst.holder}</span>
                <span className="text-[#40C4FF] font-mono flex-shrink-0">
                  {inst.pct_out != null ? inst.pct_out + '%' : '—'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Major holders rows from yfinance */}
      {!data.top_institutions?.length && data.major_holders_rows?.length > 0 && (
        <div className="space-y-px">
          {data.major_holders_rows.map((row, i) => (
            <div key={i} className="flex justify-between text-[10px] px-2 py-0.5 bg-[#111] rounded">
              <span className="text-gray-500">{row[1]}</span>
              <span className="text-gray-200 font-mono">{row[0]}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Collapsible investors section ─────────────────────────────────────────────
function InvestorsSection({ symbol }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [open, setOpen]       = useState(false)

  const load = () => {
    if (data || loading) return
    setLoading(true)
    api.getInvestors(symbol)
      .then(setData)
      .catch(() => setData({ error: '資料載入失敗' }))
      .finally(() => setLoading(false))
  }

  const toggle = () => {
    setOpen(o => !o)
    if (!open) load()
  }

  return (
    <div className="border border-[#1E1E1E] rounded overflow-hidden">
      <button
        onClick={toggle}
        className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-[#1A1A1A] transition-colors"
      >
        <span className="font-semibold text-gray-300">
          {symbol?.endsWith('.TW') || symbol?.endsWith('.TWO')
            ? '三大法人買賣超'
            : '法人 / 散戶持股分析'}
        </span>
        <span className="text-[10px] text-gray-600">{open ? '▼' : '▶'}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 border-t border-[#1E1E1E]">
          {loading && <div className="text-gray-600 text-[10px] py-3 text-center">載入中...</div>}
          {data?.error && <div className="text-yellow-600 text-[10px] py-2">{data.error}</div>}
          {data && !data.error && data.type === 'tw' && <InvestorsTW data={data} />}
          {data && !data.error && data.type === 'us' && <InvestorsUS data={data} />}
        </div>
      )}
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
          <span className={`text-base font-mono ${isUp ? 'text-[#EF5350]' : 'text-[#26A69A]'}`}>
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
            <span className="text-gray-400">支撐位: <span className="text-[#EF5350] font-mono">{data.support?.toLocaleString()}</span></span>
          )}
          {data.resistance && (
            <span className="text-gray-400">壓力位: <span className="text-[#26A69A] font-mono">{data.resistance?.toLocaleString()}</span></span>
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

      {/* Investor / institutional data */}
      <InvestorsSection symbol={symbol} />

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
          report.market_sentiment === '多頭' ? 'bg-[#2A0A0A] text-[#EF5350]' :
          report.market_sentiment === '空頭' ? 'bg-[#0A2A0A] text-[#26A69A]' :
          'bg-[#1A1A0A] text-[#FFA726]'
        }`}>
          市場情緒: {report.market_sentiment}
        </div>
      </div>

      {/* Top Opportunities */}
      {report.top_opportunities?.length > 0 && (
        <div>
          <div className="text-sm font-semibold text-[#EF5350] mb-2">買入機會 TOP 5</div>
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
          <div className="text-sm font-semibold text-[#26A69A] mb-2">風險警示 TOP 5</div>
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
                info.sentiment === '多頭' ? 'text-[#EF5350]' :
                info.sentiment === '空頭' ? 'text-[#26A69A]' : 'text-[#FFA726]'
              }`}>
                {info.sentiment} ({info.avg_score > 0 ? '+' : ''}{info.avg_score})
              </span>
            </div>
          ))}
        </div>
      </div>

      <TrumpNewsReportSummary data={report.trump_news} />

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
                  <span className={`text-[10px] ${r.daily_change_pct >= 0 ? 'text-[#EF5350]' : 'text-[#26A69A]'}`}>
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
