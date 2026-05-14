import { useEffect, useState } from 'react'
import { api } from '../api/stocks.js'
import { UpdateTime, formatUpdateTime } from '../utils/time.jsx'

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
const fmtEtfDelta = chg => {
  if (!chg) return ''
  if (chg.change_basis === 'weight' && chg.weight_delta != null) {
    const delta = Number(chg.weight_delta)
    return `${delta > 0 ? '+' : ''}${delta.toFixed(2)}pp`
  }
  if (chg.shares_delta != null) {
    const delta = Number(chg.shares_delta)
    return `${delta > 0 ? '+' : ''}${delta.toLocaleString()}`
  }
  return ''
}

// ── TW: 三大法人 ──────────────────────────────────────────────────────────────
function ThreeForcesPanel({ data }) {
  const trend   = data.trend || []
  const maxAbs  = Math.max(...trend.map(d => Math.abs(d.foreign_net)), 1)

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <UpdateTime value={data.last_updated || data.latest_date} />
      </div>
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
      <div className="flex justify-end">
        <UpdateTime value={margin.last_updated || margin.latest_date} />
      </div>
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
          <UpdateTime value={data.last_updated || data.latest_date} />
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
      <div className="flex items-center gap-2 border-b border-[#1E1E1E] pb-1">
        <div className="flex gap-1">
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
        <div className="ml-auto">
          <UpdateTime value={tab === 'margin' ? (data.margin?.last_updated || data.margin_last_updated) : data.last_updated} />
        </div>
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

// ── Sector colours ────────────────────────────────────────────────────────────
const SECTOR_COLORS = {
  '半導體':     '#40C4FF',
  '科技系統廠': '#26A69A',
  '電子零組件': '#80DEEA',
  '其他電子':   '#90A4AE',
  '通信網路':   '#64B5F6',
  '鋼鐵':       '#A1887F',
  '電機機械':   '#A5D6A7',
  '電器電纜':   '#FFCC80',
  '資源':       '#FF9800',
  '金融':       '#CE93D8',
  '電信':       '#66BB6A',
  '太陽能':     '#FFF176',
  '太陽能/綠能': '#FFF176',
  'AI與雲端':   '#7E57C2',
  '資訊服務':   '#4FC3F7',
  '電子通路':   '#FFB74D',
  '化工/塑化':  '#FF7043',
  '傳產':       '#90A4AE',
  '航運':       '#4DD0E1',
  '零售':       '#F48FB1',
  '生技醫療':   '#B39DDB',
  '光學':       '#80CBC4',
  '機械':       '#A5D6A7',
  '汽車':       '#FFCC80',
  '水泥':       '#BCAAA4',
  '食品':       '#E6EE9C',
  'PCB':        '#80DEEA',
  '紡織':       '#FFAB91',
  '建設':       '#CFD8DC',
  '交通':       '#B0BEC5',
  '能源':       '#FFA726',
  '觀光餐旅':   '#AED581',
  '居家生活':   '#D7CCC8',
  '主動式ETF':  '#5C6BC0',
  '其他':       '#37474F',
}

// ── SVG donut chart ───────────────────────────────────────────────────────────
function SvgDonutChart({ slices, size = 140 }) {
  const total = slices.reduce((s, x) => s + x.value, 0)
  if (!total || !slices.length) return null
  const cx = size / 2, cy = size / 2
  const ro = size * 0.46, ri = size * 0.27

  let angle = -Math.PI / 2
  const arcs = slices.filter(s => s.value > 0).map(s => {
    const span = (s.value / total) * 2 * Math.PI
    const end  = angle + span
    const ox1 = cx + ro * Math.cos(angle), oy1 = cy + ro * Math.sin(angle)
    const ox2 = cx + ro * Math.cos(end),   oy2 = cy + ro * Math.sin(end)
    const ix1 = cx + ri * Math.cos(end),   iy1 = cy + ri * Math.sin(end)
    const ix2 = cx + ri * Math.cos(angle), iy2 = cy + ri * Math.sin(angle)
    const large = span > Math.PI ? 1 : 0
    const d = `M ${ox1} ${oy1} A ${ro} ${ro} 0 ${large} 1 ${ox2} ${oy2} ` +
              `L ${ix1} ${iy1} A ${ri} ${ri} 0 ${large} 0 ${ix2} ${iy2} Z`
    const pct = (s.value / total * 100).toFixed(1)
    angle = end
    return { ...s, d, pct }
  })

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {arcs.map((a, i) => (
        <path key={i} d={a.d} fill={a.color} stroke="#0D0D0D" strokeWidth="1.5" opacity="0.92">
          <title>{a.label}: {a.pct}%</title>
        </path>
      ))}
    </svg>
  )
}

// ── Active ETF sector overview (for DailyReport) ──────────────────────────────
function EtfSectorOverview() {
  const [allData, setAllData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    api.getAllEtfHoldings()
      .then(setAllData)
      .catch(() => setAllData(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="text-[10px] text-gray-600 py-1">主動式ETF產業資料載入中...</div>
  )
  if (!allData) return null

  // Aggregate sector weights across all stock-type (A) active ETFs
  const sectorAgg = {}       // sector → cumulative weight
  const sectorStocks = {}    // sector → { code → {name, totalWeight, etfCount} }

  for (const [etfCode, etfData] of Object.entries(allData)) {
    if (etfCode.endsWith('D')) continue   // skip bond ETFs
    if (etfData.error || !etfData.holdings?.length) continue
    for (const h of etfData.holdings) {
      const sec = h.sector || '其他'
      const w   = h.weight_pct || 0
      sectorAgg[sec] = (sectorAgg[sec] || 0) + w
      if (!sectorStocks[sec]) sectorStocks[sec] = {}
      const code = h.stock_code || ''
      if (code) {
        if (!sectorStocks[sec][code]) {
          sectorStocks[sec][code] = { name: h.stock_name || code, totalWeight: 0, etfCount: 0 }
        }
        sectorStocks[sec][code].totalWeight += w
        sectorStocks[sec][code].etfCount++
      }
    }
  }

  const totalW = Object.values(sectorAgg).reduce((s, v) => s + v, 0)
  if (!totalW) return null
  const allUpdatedAt = Object.values(allData || {})
    .map(item => item?.last_updated || item?.fetched_at || '')
    .filter(Boolean)
    .sort()
    .pop()

  const sectors = Object.entries(sectorAgg)
    .sort(([, a], [, b]) => b - a)
    .map(([name, weight]) => ({
      name,
      weight: +weight.toFixed(2),
      pct:    +(weight / totalW * 100).toFixed(1),
      color:  SECTOR_COLORS[name] || SECTOR_COLORS['其他'],
      topStocks: Object.entries(sectorStocks[name] || {})
        .sort(([, a], [, b]) => b.totalWeight - a.totalWeight)
        .slice(0, 6)
        .map(([code, info]) => ({ code, ...info, totalWeight: +info.totalWeight.toFixed(2) })),
    }))

  const pieSlices = sectors.slice(0, 14).map(s => ({
    label: s.name, value: s.weight, color: s.color,
  }))

  return (
    <div>
      <div className="text-sm font-semibold text-[#40C4FF] mb-2">
        📊 主動式ETF 產業配置分析（股票型彙整）
      </div>
      <div className="bg-[#101214] border border-[#1E2833] rounded p-3 space-y-3">
        <div className="flex justify-end">
          <UpdateTime value={allUpdatedAt} />
        </div>

        {/* Pie + legend row */}
        <div className="flex gap-4 items-start">
          <div className="flex-shrink-0">
            <SvgDonutChart slices={pieSlices} size={140} />
          </div>
          <div className="flex-1 min-w-0 space-y-1">
            <div className="text-[9px] text-gray-600 mb-1.5">各產業累計持倉權重加總</div>
            {sectors.slice(0, 12).map(s => (
              <div key={s.name} className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-sm flex-shrink-0" style={{ background: s.color }} />
                <span className="text-[10px] text-gray-300 truncate w-20 flex-shrink-0">{s.name}</span>
                <div className="flex-1 h-1.5 bg-[#1A1A1A] rounded overflow-hidden">
                  <div className="h-full rounded" style={{ width: `${s.pct}%`, background: s.color, opacity: 0.75 }} />
                </div>
                <span className="text-[10px] font-mono text-gray-400 w-9 text-right flex-shrink-0">{s.pct}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Expand/collapse individual sector stock lists */}
        <button
          onClick={() => setExpanded(e => !e)}
          className="text-[9px] text-gray-600 hover:text-gray-400 transition-colors w-full text-left border-t border-[#1E1E1E] pt-2"
        >
          {expanded ? '▲ 收起個股明細' : '▼ 展開各產業個股明細'}
        </button>

        {expanded && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
            {sectors.slice(0, 12).map(s => (
              <div key={s.name} className="bg-[#0A0D10] rounded p-2">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: s.color }} />
                  <span className="text-[11px] font-semibold text-gray-100">{s.name}</span>
                  <span className="text-[9px] text-gray-600 ml-auto">{s.pct}% 合計</span>
                </div>
                {s.topStocks.map(st => (
                  <div key={st.code} className="flex items-center gap-1 py-0.5 border-b border-[#0F1215] last:border-0 text-[9px]">
                    <span className="text-[#40C4FF] font-mono w-10 flex-shrink-0">{st.code}</span>
                    <span className="text-gray-400 flex-1 truncate">{st.name}</span>
                    <span className="text-[#FFA726] font-mono flex-shrink-0">{st.totalWeight}%</span>
                    {st.etfCount > 1 && (
                      <span className="text-gray-700 flex-shrink-0 ml-0.5">{st.etfCount}檔</span>
                    )}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
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
              <span className="text-gray-700">持股日: {data.date}</span>
              <span className="ml-auto"><UpdateTime value={data.last_updated || data.fetched_at || data.date} /></span>
            </div>

            {/* Change summary (vs previous trading day) */}
            {data.changes && (
              <div className="bg-[#0A0A14] border border-[#1E1E3A] rounded px-2 py-1.5 flex flex-wrap gap-2 text-[10px]">
                <span className="text-gray-600 mr-1">較前日:</span>
                {data.changes.available === false ? (
                  <span className="text-yellow-500">{data.changes.reason || '尚未取得前一交易日持倉'}</span>
                ) : (
                  <>
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
                  </>
                )}
                {data.changes.prev_date && (
                  <span className="ml-auto text-gray-700">前次: {data.changes.prev_date}</span>
                )}
              </div>
            )}

            {/* Holdings table */}
            {data.holdings?.length > 0 && (() => {
              // Build change lookup by stock_code
              const changeMap = {}
              if (data.changes) {
                for (const h of (data.changes.new_positions || []))
                  changeMap[h.stock_code] = { type: 'new' }
                for (const h of (data.changes.increased || []))
                  changeMap[h.stock_code] = { type: 'up', row: h }
                for (const h of (data.changes.decreased || []))
                  changeMap[h.stock_code] = { type: 'down', row: h }
              }

              // Compute ±% change (prefer weight_delta pp, else shares pct)
              const getChgPct = (chg) => {
                if (!chg || chg.type === 'new') return null
                const r = chg.row || {}
                if (r.change_basis === 'weight' && r.weight_delta != null)
                  return { v: +Number(r.weight_delta).toFixed(2), unit: 'pp' }
                if (r.shares_delta != null && r.prev_shares > 0)
                  return { v: +(r.shares_delta / r.prev_shares * 100).toFixed(1), unit: '%' }
                return null
              }

              return (
                <div className="max-h-80 overflow-y-auto">
                  {/* table-fixed prevents columns from overflowing container */}
                  <table className="w-full text-[10px] table-fixed">
                    <colgroup>
                      <col className="w-5" />
                      <col className="w-[38px]" />
                      <col />  {/* name: takes remaining space */}
                      <col className="w-[44px]" />
                      <col className="w-[48px]" />
                    </colgroup>
                    <thead className="sticky top-0 bg-[#0D0D0D]">
                      <tr className="text-gray-600 border-b border-[#1E1E1E]">
                        <td className="py-1">#</td>
                        <td className="py-1">代號</td>
                        <td className="py-1">名稱</td>
                        <td className="py-1 text-right text-[#FFA726]">占比</td>
                        <td className="py-1 text-right">變化</td>
                      </tr>
                    </thead>
                    <tbody>
                      {data.holdings.map((h, i) => {
                        const chg    = changeMap[h.stock_code]
                        const chgPct = getChgPct(chg)
                        const chgCell = chg
                          ? chg.type === 'new'
                            ? <span className="text-[#26A69A] font-bold text-[9px]">NEW</span>
                            : chgPct
                              ? chg.type === 'up'
                                ? <span className="text-[#40C4FF]">↑{chgPct.v}%</span>
                                : <span className="text-[#FFA726]">↓{Math.abs(chgPct.v)}%</span>
                              : chg.type === 'up'
                                ? <span className="text-[#40C4FF]">↑</span>
                                : <span className="text-[#FFA726]">↓</span>
                          : <span className="text-gray-800">─</span>
                        return (
                          <tr key={i} className={`border-b border-[#111] hover:bg-[#111] ${chg ? 'bg-[#0A0A12]' : ''}`}>
                            <td className="py-1 text-gray-700">{i + 1}</td>
                            <td className="py-1 font-mono text-[#40C4FF] truncate">{h.stock_code || '—'}</td>
                            <td className="py-1 text-gray-300 truncate overflow-hidden">{h.stock_name || '—'}</td>
                            <td className="py-1 text-right font-mono">
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
        <span className="ml-auto mr-2">
          <UpdateTime value={data?.last_updated} />
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
          <div className="mt-1"><UpdateTime value={data.last_updated || data.generated_at} /></div>
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
        最後更新: {formatUpdateTime(data.last_updated || data.generated_at)}
      </div>
    </div>
  )
}

function DailyReport({ refreshToken = 0 }) {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = () => {
    setLoading(true)
    setError(null)
    api.getDailyReport()
      .then(setReport)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [refreshToken])

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
          <UpdateTime value={report.last_updated || report.generated_at} />
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

export default function AnalysisPanel({ symbol, stockName, mode, reportVersion }) {
  if (mode === 'report') return <DailyReport refreshToken={reportVersion} />
  return <SingleAnalysis symbol={symbol} stockName={stockName} />
}

// ── DataStatusPanel (exported for App.jsx) ────────────────────────────────────
function ageMinutes(ts) {
  if (!ts) return null
  try {
    const d = new Date(ts.replace(' ', 'T'))
    if (isNaN(d)) return null
    return (Date.now() - d.getTime()) / 60000
  } catch { return null }
}

function StatusDot({ ts, errorField }) {
  if (errorField) return <span className="text-[#EF5350] font-bold">● 錯誤</span>
  const age = ageMinutes(ts)
  if (age === null) return <span className="text-gray-600">● 未知</span>
  if (age < 360)   return <span className="text-[#26A69A] font-bold">● 正常</span>
  if (age < 2160)  return <span className="text-[#FFA726] font-bold">● 偏舊</span>
  return                   <span className="text-[#EF5350] font-bold">● 未更新</span>
}

function StatusAge({ ts }) {
  const age = ageMinutes(ts)
  if (!ts || age === null) return <span className="text-gray-700">—</span>
  // Format: MM-DD HH:mm
  try {
    const d = new Date(ts.replace(' ', 'T'))
    const mm = String(d.getMonth()+1).padStart(2,'0')
    const dd = String(d.getDate()).padStart(2,'0')
    const hh = String(d.getHours()).padStart(2,'0')
    const min = String(d.getMinutes()).padStart(2,'0')
    const ageH = Math.round(age / 60)
    const ageLabel = age < 60 ? `${Math.round(age)}分前` : ageH < 48 ? `${ageH}小時前` : `${Math.round(ageH/24)}天前`
    return (
      <span>
        <span className="text-gray-300">{mm}-{dd} {hh}:{min}</span>
        <span className="text-gray-600 ml-1 text-[9px]">({ageLabel})</span>
      </span>
    )
  } catch { return <span className="text-gray-400">{ts}</span> }
}

export function DataStatusPanel() {
  const [health, setHealth] = useState(null)
  const [etfData, setEtfData] = useState(null)
  const [newsData, setNewsData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [checkedAt, setCheckedAt] = useState(null)

  const reload = () => {
    setLoading(true)
    Promise.allSettled([
      api.getHealth(),
      api.getAllEtfHoldings(),
      api.getNews(),
    ]).then(([h, etf, news]) => {
      if (h.status === 'fulfilled')   setHealth(h.value)
      if (etf.status === 'fulfilled') setEtfData(etf.value)
      if (news.status === 'fulfilled') setNewsData(news.value)
      setCheckedAt(new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' }))
      setLoading(false)
    })
  }

  useEffect(() => { reload() }, [])

  const rs = health?.refresh_status || {}

  // Determine ETF last_updated: look at per-ETF entries in etfData
  const etfTs = (() => {
    if (!etfData) return null
    const entries = Object.values(etfData)
    const times = entries.map(e => e.last_updated || e.fetched_at).filter(Boolean)
    if (!times.length) return null
    return times.sort().at(-1)   // most recent
  })()

  // News last_updated: try category last_updated
  const newsTs = (() => {
    if (!newsData) return null
    if (newsData.last_updated) return newsData.last_updated
    const cats = Object.values(newsData.categories || {})
    const times = cats.map(c => c.last_updated).filter(Boolean)
    return times.sort().at(-1) || null
  })()

  const rows = [
    {
      name: '後台服務',
      source: 'Railway',
      schedule: '常駐',
      ts: health ? new Date().toISOString() : null,
      err: health?.status !== 'ok' ? health?.status : null,
      extra: health ? `已分析 ${health.stocks_analyzed} 支股票` : null,
    },
    {
      name: '股票分析',
      source: 'yfinance / FinMind',
      schedule: '18:30 每日',
      ts: rs.evening_data_refresh?.last_updated,
      err: rs.evening_data_refresh?.error,
      extra: (() => {
        const s = rs.evening_data_refresh
        if (!s) return null
        const parts = []
        if (s.ok != null) parts.push(`✅ ${s.ok}支`)
        if (s.errors != null) parts.push(`❌ ${s.errors}支`)
        if (s.duration_seconds != null) parts.push(`耗時 ${s.duration_seconds}s`)
        return parts.join('  ')
      })(),
    },
    {
      name: 'ETF持倉',
      source: '公開資訊觀測站',
      schedule: '15:00 每日',
      ts: rs.etf_holdings?.last_updated || etfTs,
      err: rs.etf_holdings?.error,
      extra: rs.etf_holdings
        ? `✅ ${rs.etf_holdings.ok ?? '?'}支 / ❌ ${rs.etf_holdings.errors ?? '?'}支`
        : null,
    },
    {
      name: 'Trump新聞',
      source: 'NewsAPI',
      schedule: '每5小時',
      ts: health?.trump_news_last_updated,
      err: null,
      extra: null,
    },
    {
      name: '一般新聞',
      source: 'NewsAPI',
      schedule: '每5小時',
      ts: newsTs,
      err: null,
      extra: null,
    },
    {
      name: '資料健康報告',
      source: '內部監控',
      schedule: '19:00 每日',
      ts: rs.data_health_check?.last_updated,
      err: rs.data_health_check?.error,
      extra: (() => {
        const d = rs.data_health_check
        if (!d) return null
        if (d.summary_counts) {
          const c = d.summary_counts
          return `正常 ${c.ok ?? 0} / 警告 ${c.warning ?? 0} / 錯誤 ${c.error ?? 0}`
        }
        return d.status_label || null
      })(),
    },
  ]

  return (
    <div className="p-4 overflow-y-auto h-full">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-lg font-bold text-white">數據狀態監控</div>
          <div className="text-xs text-gray-500">各模組資料抓取時效確認（非即時數值）</div>
        </div>
        <div className="flex items-center gap-3">
          {checkedAt && <span className="text-[10px] text-gray-600">最後檢查 {checkedAt}</span>}
          <button
            onClick={reload}
            disabled={loading}
            className="px-3 py-1 text-xs bg-[#1A2A1A] hover:bg-[#223322] text-green-400 rounded border border-[#2A3A2A] disabled:opacity-40 transition-colors"
          >
            {loading ? '更新中...' : '↻ 重新檢查'}
          </button>
        </div>
      </div>

      {loading && !health ? (
        <div className="text-gray-500 text-sm py-8 text-center">載入中...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="text-gray-500 border-b border-[#2A2A2A]">
                <th className="text-left py-2 pr-4 font-medium">模組</th>
                <th className="text-left py-2 pr-4 font-medium">資料來源</th>
                <th className="text-left py-2 pr-4 font-medium">排程</th>
                <th className="text-left py-2 pr-4 font-medium">最後更新</th>
                <th className="text-left py-2 pr-4 font-medium">狀態</th>
                <th className="text-left py-2 font-medium">備註</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(row => (
                <tr key={row.name} className="border-b border-[#1A1A1A] hover:bg-[#141414]">
                  <td className="py-2.5 pr-4 font-semibold text-gray-200">{row.name}</td>
                  <td className="py-2.5 pr-4 text-gray-500">{row.source}</td>
                  <td className="py-2.5 pr-4 text-gray-400 font-mono">{row.schedule}</td>
                  <td className="py-2.5 pr-4 font-mono text-sm">
                    <StatusAge ts={row.ts} />
                  </td>
                  <td className="py-2.5 pr-4 text-sm">
                    <StatusDot ts={row.ts} errorField={row.err} />
                  </td>
                  <td className="py-2.5 text-[10px] text-gray-600">{row.extra || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Raw refresh_status detail */}
      {health && Object.keys(rs).length > 0 && (
        <details className="mt-6">
          <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-400">
            ▶ 原始排程日誌
          </summary>
          <div className="mt-2 space-y-2">
            {Object.entries(rs).map(([key, val]) => (
              <div key={key} className="bg-[#111] rounded p-2 text-[10px]">
                <div className="text-gray-400 font-semibold mb-1">{key}</div>
                <pre className="text-gray-600 whitespace-pre-wrap font-mono">
                  {JSON.stringify(val, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}
