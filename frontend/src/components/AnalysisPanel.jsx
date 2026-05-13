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

// ── helpers ───────────────────────────────────────────────────────────────────
const fmtNet = v => {
  if (v == null) return '—'
  const abs = Math.abs(v)
  const sign = v >= 0 ? '+' : '-'
  if (abs >= 10000) return `${sign}${(abs / 10000).toFixed(1)}萬`
  return `${sign}${abs.toLocaleString()}`
}
const fmtK = v => {
  if (v == null) return '—'
  if (v >= 10000) return `${(v / 10000).toFixed(1)}萬`
  return v.toLocaleString()
}

// ── TW: 三大法人 ──────────────────────────────────────────────────────────────
function ThreeForcesPanel({ data }) {
  const trend   = data.trend || []
  const maxAbs  = Math.max(...trend.map(d => Math.abs(d.foreign_net)), 1)

  return (
    <div className="space-y-3">
      {/* 三大法人最新數字 */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: '外資', val: data.foreign_net, color: '#40C4FF' },
          { label: '投信', val: data.trust_net,   color: '#AB47BC' },
          { label: '自營商', val: data.dealer_net, color: '#FFA726' },
        ].map(({ label, val }) => (
          <div key={label} className="bg-[#111] rounded p-2 text-center border border-[#1E1E1E]">
            <div className="text-[9px] text-gray-500 mb-1">{label}買賣超</div>
            <div className={`text-sm font-mono font-bold ${val >= 0 ? 'text-[#EF5350]' : 'text-[#26A69A]'}`}>
              {fmtNet(val)}
            </div>
            <div className="text-[9px] text-gray-600">張</div>
          </div>
        ))}
      </div>

      {/* 外資趨勢柱圖 */}
      {trend.length > 1 && (
        <div>
          <div className="text-[9px] text-gray-500 mb-1">外資近{trend.length}日買賣超趨勢</div>
          <div className="flex items-stretch gap-0.5 h-16 bg-[#0A0A0A] rounded p-1">
            {trend.map((d, i) => {
              const pct = Math.abs(d.foreign_net) / maxAbs
              const isPos = d.foreign_net >= 0
              return (
                <div key={i} className="flex-1 flex flex-col items-center"
                  title={`${d.date}: ${fmtNet(d.foreign_net)}張`}>
                  <div className="w-full flex-1 flex items-end">
                    {isPos && <div className="w-full rounded-sm" style={{ height: `${pct*100}%`, minHeight: 2, background: '#EF5350' }} />}
                  </div>
                  <div className="w-full flex-1 flex items-start">
                    {!isPos && <div className="w-full rounded-sm" style={{ height: `${pct*100}%`, minHeight: 2, background: '#26A69A' }} />}
                  </div>
                </div>
              )
            })}
          </div>
          <div className="flex justify-between text-[9px] text-gray-600 mt-0.5">
            <span>{trend[0]?.date?.slice(5)}</span>
            <span>{trend[trend.length-1]?.date?.slice(5)}</span>
          </div>
        </div>
      )}

      {/* 三大合計 + 日期 */}
      <div className="flex items-center justify-between bg-[#0D1A0D] rounded px-3 py-2 border border-[#1A2A1A]">
        <span className="text-xs text-gray-400">三大法人合計</span>
        <span className={`text-base font-mono font-bold ${data.total_net >= 0 ? 'text-[#EF5350]' : 'text-[#26A69A]'}`}>
          {fmtNet(data.total_net)} 張
        </span>
        <span className="text-[10px] text-gray-600">{data.latest_date} {data.market}</span>
      </div>

      {/* 5日明細表 */}
      {trend.length > 0 && (
        <div>
          <div className="text-[9px] text-gray-500 mb-1">近5日明細</div>
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="text-gray-600 border-b border-[#1E1E1E]">
                  <td className="py-1 pr-2">日期</td>
                  <td className="py-1 pr-2 text-right text-[#40C4FF]">外資</td>
                  <td className="py-1 pr-2 text-right text-[#AB47BC]">投信</td>
                  <td className="py-1 pr-2 text-right text-[#FFA726]">自營</td>
                  <td className="py-1 text-right">合計</td>
                </tr>
              </thead>
              <tbody>
                {[...trend].reverse().map((d, i) => (
                  <tr key={i} className="border-b border-[#111] hover:bg-[#111]">
                    <td className="py-1 pr-2 text-gray-500">{d.date?.slice(5)}</td>
                    <td className={`py-1 pr-2 text-right font-mono ${d.foreign_net >= 0 ? 'text-[#EF5350]' : 'text-[#26A69A]'}`}>{fmtNet(d.foreign_net)}</td>
                    <td className={`py-1 pr-2 text-right font-mono ${d.trust_net   >= 0 ? 'text-[#EF5350]' : 'text-[#26A69A]'}`}>{fmtNet(d.trust_net)}</td>
                    <td className={`py-1 pr-2 text-right font-mono ${d.dealer_net  >= 0 ? 'text-[#EF5350]' : 'text-[#26A69A]'}`}>{fmtNet(d.dealer_net)}</td>
                    <td className={`py-1 text-right font-mono font-bold ${d.total_net >= 0 ? 'text-[#EF5350]' : 'text-[#26A69A]'}`}>{fmtNet(d.total_net)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ── TW: 融資融券 ──────────────────────────────────────────────────────────────
function MarginPanel({ margin }) {
  if (!margin || margin.error) {
    return <div className="text-[10px] text-gray-600 py-2 text-center">{margin?.error || '無融資融券資料'}</div>
  }

  const trend = margin.trend || []
  const maxBal = Math.max(...trend.map(t => t.margin_bal), 1)

  const ratio = margin.margin_short_ratio
  const ratioLabel = ratio == null ? '—' : ratio > 15 ? '多方明顯主導' : ratio > 8 ? '多方略優' : ratio > 3 ? '均衡' : '空方壓力'
  const ratioColor = ratio == null ? 'text-gray-500' : ratio > 8 ? 'text-[#EF5350]' : ratio > 3 ? 'text-[#FFA726]' : 'text-[#26A69A]'

  return (
    <div className="space-y-3">
      {/* 融資 / 融券 餘額卡片 */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-[#111] rounded p-2 border border-[#1E1E1E]">
          <div className="text-[9px] text-gray-500 mb-1">融資餘額</div>
          <div className="text-sm font-mono text-[#40C4FF] font-bold">{fmtK(margin.margin_bal)}</div>
          <div className="flex justify-between mt-1.5 text-[9px] text-gray-600">
            <span>↑買進 {fmtK(margin.margin_buy)}</span>
            <span>↓賣出 {fmtK(margin.margin_sell)}</span>
          </div>
        </div>
        <div className="bg-[#111] rounded p-2 border border-[#1E1E1E]">
          <div className="text-[9px] text-gray-500 mb-1">融券餘額（空單）</div>
          <div className="text-sm font-mono text-[#EF5350] font-bold">{fmtK(margin.short_bal)}</div>
          <div className="flex justify-between mt-1.5 text-[9px] text-gray-600">
            <span>↓賣出 {fmtK(margin.short_sell)}</span>
            <span>↑回補 {fmtK(margin.short_buy)}</span>
          </div>
        </div>
      </div>

      {/* 資券比 */}
      <div className="flex items-center justify-between bg-[#111] rounded px-3 py-2 border border-[#1E1E1E]">
        <span className="text-xs text-gray-400">資券比</span>
        <span className={`text-base font-mono font-bold ${ratioColor}`}>
          {ratio != null ? ratio.toFixed(1) + 'x' : '—'}
        </span>
        <span className={`text-[10px] ${ratioColor}`}>{ratioLabel}</span>
      </div>

      {/* 融資餘額趨勢 */}
      {trend.length > 1 && (
        <div>
          <div className="text-[9px] text-gray-500 mb-1">融資餘額近{trend.length}日趨勢</div>
          <div className="flex items-end gap-0.5 h-10 bg-[#0A0A0A] rounded p-1">
            {trend.map((d, i) => (
              <div key={i} className="flex-1 flex items-end"
                title={`${d.date}: 融資${fmtK(d.margin_bal)} 融券${fmtK(d.short_bal)}`}>
                <div className="w-full rounded-sm"
                  style={{ height: `${Math.max(d.margin_bal/maxBal*100, 5)}%`, background: '#40C4FF88' }} />
              </div>
            ))}
          </div>
          <div className="flex justify-between text-[9px] text-gray-600 mt-0.5">
            <span>{trend[0]?.date?.slice(5)}</span>
            <span>{trend[trend.length-1]?.date?.slice(5)}</span>
          </div>
        </div>
      )}

      {/* 5日明細表 */}
      {trend.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="text-gray-600 border-b border-[#1E1E1E]">
                <td className="py-1 pr-2">日期</td>
                <td className="py-1 pr-2 text-right text-[#40C4FF]">融資餘額</td>
                <td className="py-1 pr-2 text-right text-[#EF5350]">融券餘額</td>
                <td className="py-1 text-right text-[#FFA726]">資券比</td>
              </tr>
            </thead>
            <tbody>
              {[...trend].reverse().map((d, i) => (
                <tr key={i} className="border-b border-[#111] hover:bg-[#111]">
                  <td className="py-1 pr-2 text-gray-500">{d.date?.slice(5)}</td>
                  <td className="py-1 pr-2 text-right font-mono text-[#40C4FF]">{fmtK(d.margin_bal)}</td>
                  <td className="py-1 pr-2 text-right font-mono text-[#EF5350]">{fmtK(d.short_bal)}</td>
                  <td className="py-1 text-right font-mono text-[#FFA726]">
                    {d.margin_short_ratio != null ? d.margin_short_ratio.toFixed(1)+'x' : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="text-[9px] text-gray-700">{margin.latest_date} · {margin.market}</div>
    </div>
  )
}

// ── TW: 主力動向（三大法人行為分析）─────────────────────────────────────────
function MajorForcePanel({ data }) {
  const total = data.total_net ?? 0
  const foreign = data.foreign_net ?? 0
  const trust   = data.trust_net   ?? 0
  const dealer  = data.dealer_net  ?? 0
  const trend   = data.trend || []

  // 主力判斷邏輯
  const sentiment = total > 0 ? '主力買超，籌碼偏多' : total < 0 ? '主力賣超，籌碼偏空' : '主力中立'
  const sentColor = total > 0 ? 'text-[#EF5350]' : total < 0 ? 'text-[#26A69A]' : 'text-[#FFA726]'

  // 連續買超/賣超天數
  let streak = 0
  const dir = total >= 0 ? 1 : -1
  for (const d of [...trend].reverse()) {
    if ((d.total_net >= 0 ? 1 : -1) === dir) streak++
    else break
  }

  // 外資主導性
  const foreignDominance = Math.abs(foreign) > Math.abs(trust) + Math.abs(dealer)

  return (
    <div className="space-y-3">
      {/* 主力訊號卡 */}
      <div className="bg-[#0D1020] border border-[#1E2A3A] rounded p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-400 font-semibold">主力動向判讀</span>
          <span className="text-[9px] text-gray-600">{data.latest_date}</span>
        </div>
        <div className={`text-sm font-bold ${sentColor} mb-2`}>{sentiment}</div>
        <div className="grid grid-cols-2 gap-2 text-[10px]">
          <div className="flex items-center gap-1">
            <span className="text-gray-500">連續{dir > 0 ? '買超' : '賣超'}</span>
            <span className={`font-mono font-bold ${sentColor}`}>{streak} 日</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-gray-500">主導方</span>
            <span className="font-bold text-[#40C4FF]">{foreignDominance ? '外資主導' : '投信/自營主導'}</span>
          </div>
        </div>
      </div>

      {/* 各方力道比較 */}
      <div>
        <div className="text-[9px] text-gray-500 mb-1.5">各方力道（張）</div>
        {[
          { label: '外資', val: foreign, color: '#40C4FF' },
          { label: '投信', val: trust,   color: '#AB47BC' },
          { label: '自營商', val: dealer, color: '#FFA726' },
        ].map(({ label, val, color }) => {
          const maxVal = Math.max(Math.abs(foreign), Math.abs(trust), Math.abs(dealer), 1)
          const barPct = Math.abs(val) / maxVal * 100
          return (
            <div key={label} className="flex items-center gap-2 mb-1.5">
              <span className="text-[9px] text-gray-500 w-12 flex-shrink-0">{label}</span>
              <div className="flex-1 h-3 bg-[#0A0A0A] rounded overflow-hidden flex">
                {val >= 0
                  ? <><div className="flex-1" /><div className="rounded-r" style={{ width: `${barPct/2}%`, background: '#EF5350' }} /></>
                  : <><div className="rounded-l" style={{ width: `${barPct/2}%`, background: '#26A69A' }} /><div className="flex-1" /></>
                }
              </div>
              <span className={`text-[10px] font-mono w-16 text-right ${val >= 0 ? 'text-[#EF5350]' : 'text-[#26A69A]'}`}>
                {fmtNet(val)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── TW: 完整法人面板（含三個子分頁）────────────────────────────────────────────
function InvestorsTW({ data }) {
  const [tab, setTab] = useState('major')
  const tabs = [
    { key: 'major',  label: '主力動向' },
    { key: 'three',  label: '三大法人' },
    { key: 'margin', label: '融資融券' },
  ]

  return (
    <div className="space-y-2 pt-1">
      {/* Tab bar */}
      <div className="flex gap-1 border-b border-[#1E1E1E] pb-1">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-3 py-1 text-xs rounded-t transition-colors ${
              tab === t.key
                ? 'bg-[#1A1A2E] text-white border border-[#2A2A4A] border-b-transparent'
                : 'text-gray-500 hover:text-gray-300'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'major'  && <MajorForcePanel  data={data} />}
      {tab === 'three'  && <ThreeForcesPanel data={data} />}
      {tab === 'margin' && <MarginPanel      margin={data.margin} />}
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

// ── Helpers ───────────────────────────────────────────────────────────────────
const isActiveETF = (symbol) => {
  const u = (symbol || '').toUpperCase().replace('.TW', '')
  return /^\d{5}[AD]$/.test(u)
}

// ── Active ETF holdings panel ─────────────────────────────────────────────────
function EtfHoldingsPanel({ symbol }) {
  const code = symbol.toUpperCase().replace('.TW', '')
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = (refresh = false) => {
    if (refresh) setRefreshing(true)
    else setLoading(true)
    api.getEtfHoldings(code, refresh)
      .then(d => { setData(d); setLoading(false); setRefreshing(false) })
      .catch(() => { setData({ error: '無法載入持倉資料' }); setLoading(false); setRefreshing(false) })
  }

  useEffect(() => { load() }, [symbol])  // eslint-disable-line react-hooks/exhaustive-deps

  const etfType = code.endsWith('D') ? 'bond' : 'stock'
  const typeLabel = etfType === 'bond' ? '債券型 D' : '股票型 A'
  const typeColor = etfType === 'bond' ? 'text-[#AB47BC]' : 'text-[#40C4FF]'

  return (
    <div className="border border-[#1E1E1E] rounded overflow-hidden">
      <div className="w-full flex items-center justify-between px-3 py-2 bg-[#0D1020]">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-gray-300 text-xs">主動式ETF 投資組合</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded bg-[#1A1A2E] border border-[#2A2A4A] ${typeColor}`}>
            {typeLabel}
          </span>
        </div>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="text-[9px] text-gray-600 hover:text-gray-300 px-2 py-0.5 rounded border border-[#1E1E1E] hover:border-[#3A3A3A] transition-colors"
        >
          {refreshing ? '更新中...' : '↻ 刷新'}
        </button>
      </div>

      <div className="px-3 pb-3 border-t border-[#1E1E1E]">
        {loading && <div className="text-gray-600 text-[10px] py-3 text-center">載入中...</div>}
        {!loading && data?.error && (
          <div className="text-yellow-600 text-[10px] py-2">{data.error}</div>
        )}
        {!loading && data && !data.error && (
          <div className="space-y-2 pt-2">
            {/* Summary row */}
            <div className="flex items-center gap-2 flex-wrap text-[10px] text-gray-500">
              <span>共 <strong className="text-gray-200">{data.total_holdings}</strong> 檔持股</span>
              {data.top10_weight && (
                <span>前10大占比 <strong className="text-[#FFA726]">{data.top10_weight}%</strong></span>
              )}
              <span className="ml-auto text-gray-700">更新: {data.date}</span>
            </div>

            {/* Change summary (vs previous trading day) */}
            {data.changes && (
              <div className="bg-[#0A0A14] border border-[#1E1E3A] rounded px-2 py-1.5 flex flex-wrap gap-2 text-[10px]">
                <span className="text-gray-600 mr-1">較前日:</span>
                {data.changes.new_positions?.length > 0 && (
                  <span className="text-[#26A69A] font-semibold">
                    ＋{data.changes.new_positions.length} 新建倉
                    {' '}({data.changes.new_positions.slice(0,3).map(h => h.stock_code || h.stock_name).join('/')})
                  </span>
                )}
                {data.changes.exited?.length > 0 && (
                  <span className="text-[#EF5350] font-semibold">
                    −{data.changes.exited.length} 出清
                    {' '}({data.changes.exited.slice(0,3).map(h => h.stock_code || h.stock_name).join('/')})
                  </span>
                )}
                {data.changes.increased?.length > 0 && (
                  <span className="text-[#40C4FF]">
                    ↑{data.changes.increased.length} 加碼
                  </span>
                )}
                {data.changes.decreased?.length > 0 && (
                  <span className="text-[#FFA726]">
                    ↓{data.changes.decreased.length} 減碼
                  </span>
                )}
                {!data.changes.new_positions?.length && !data.changes.exited?.length
                  && !data.changes.increased?.length && !data.changes.decreased?.length && (
                  <span className="text-gray-700">持股無變化</span>
                )}
                {data.changes.prev_date && (
                  <span className="ml-auto text-gray-700">前次: {data.changes.prev_date}</span>
                )}
              </div>
            )}

            {/* Holdings table */}
            {data.holdings?.length > 0 && (() => {
              // Build a change lookup by stock_code for inline badges
              const changeMap = {}
              if (data.changes) {
                for (const h of (data.changes.new_positions || []))
                  changeMap[h.stock_code] = { type: 'new' }
                for (const h of (data.changes.increased || []))
                  changeMap[h.stock_code] = { type: 'up', delta: h.shares_delta }
                for (const h of (data.changes.decreased || []))
                  changeMap[h.stock_code] = { type: 'down', delta: h.shares_delta }
              }
              return (
                <div className="overflow-x-auto max-h-80 overflow-y-auto">
                  <table className="w-full text-[10px]">
                    <thead className="sticky top-0 bg-[#0D0D0D]">
                      <tr className="text-gray-600 border-b border-[#1E1E1E]">
                        <td className="py-1 pr-1 w-5">#</td>
                        <td className="py-1 pr-2">代號</td>
                        <td className="py-1 pr-2">名稱</td>
                        <td className="py-1 pr-2 text-right">持股數</td>
                        <td className="py-1 pr-2 text-right text-[#FFA726]">占比%</td>
                        <td className="py-1 text-right">變化</td>
                      </tr>
                    </thead>
                    <tbody>
                      {data.holdings.map((h, i) => {
                        const chg = changeMap[h.stock_code]
                        const chgCell = chg
                          ? chg.type === 'new'
                            ? <span className="text-[#26A69A] font-bold">NEW</span>
                            : chg.type === 'up'
                              ? <span className="text-[#40C4FF]">↑{chg.delta?.toLocaleString()}</span>
                              : <span className="text-[#FFA726]">↓{Math.abs(chg.delta)?.toLocaleString()}</span>
                          : <span className="text-gray-800">─</span>
                        return (
                          <tr key={i} className={`border-b border-[#111] hover:bg-[#111] ${chg ? 'bg-[#0A0A12]' : ''}`}>
                            <td className="py-1 pr-1 text-gray-700">{i + 1}</td>
                            <td className="py-1 pr-2 font-mono text-[#40C4FF]">{h.stock_code || '—'}</td>
                            <td className="py-1 pr-2 text-gray-300 truncate max-w-[90px]">{h.stock_name}</td>
                            <td className="py-1 pr-2 text-right font-mono text-gray-400">
                              {h.shares != null ? h.shares.toLocaleString() : '—'}
                            </td>
                            <td className="py-1 pr-2 text-right font-mono">
                              {h.weight_pct != null
                                ? <span className="text-[#FFA726]">{h.weight_pct}%</span>
                                : <span className="text-gray-700">—</span>}
                            </td>
                            <td className="py-1 text-right font-mono">{chgCell}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )
            })()}

            {/* Weight bar chart for top 10 */}
            {data.holdings?.slice(0, 10).some(h => h.weight_pct) && (
              <div className="pt-1">
                <div className="text-[9px] text-gray-600 mb-1">前10大持股占比</div>
                {data.holdings.slice(0, 10).filter(h => h.weight_pct).map((h, i) => {
                  const max = data.holdings[0]?.weight_pct || 1
                  return (
                    <div key={i} className="flex items-center gap-1 mb-0.5">
                      <span className="text-[9px] text-gray-500 w-12 truncate flex-shrink-0">
                        {h.stock_code || h.stock_name?.slice(0, 4)}
                      </span>
                      <div className="flex-1 h-2 bg-[#0A0A0A] rounded overflow-hidden">
                        <div className="h-full rounded"
                          style={{ width: `${h.weight_pct / max * 100}%`, background: '#40C4FF88' }} />
                      </div>
                      <span className="text-[9px] text-[#FFA726] w-8 text-right flex-shrink-0">
                        {h.weight_pct}%
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Collapsible investors section ─────────────────────────────────────────────
function InvestorsSection({ symbol }) {
  const isTW = symbol?.toUpperCase().endsWith('.TW') || symbol?.toUpperCase().endsWith('.TWO')
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [open, setOpen]       = useState(isTW)   // auto-open for TW stocks

  const load = () => {
    if (data || loading) return
    setLoading(true)
    api.getInvestors(symbol)
      .then(setData)
      .catch(() => setData({ error: '資料載入失敗' }))
      .finally(() => setLoading(false))
  }

  // Auto-load for TW stocks on mount
  useEffect(() => {
    if (isTW) load()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol])

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
          {isTW ? '主力動向 / 三大法人 / 融資融券' : '法人 / 散戶持股分析'}
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

      {/* Active ETF holdings (only for 主動式ETF) */}
      {isActiveETF(symbol) && <EtfHoldingsPanel symbol={symbol} />}

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
