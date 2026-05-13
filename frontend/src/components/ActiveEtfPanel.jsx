import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api/stocks.js'

const CHANGE_LABELS = {
  day: '1日',
  week: '1週',
  month: '1月',
}

function fmt(value, digits = 2) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '0'
  return n.toFixed(digits)
}

function fmtDate(value) {
  if (!value) return '尚無'
  try {
    const d = new Date(value)
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleDateString('zh-TW', { month: '2-digit', day: '2-digit' })
    }
  } catch {
    // keep raw value
  }
  return value
}

function signed(value, digits = 2, suffix = '') {
  const n = Number(value)
  if (!Number.isFinite(n)) return '尚無'
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(digits)}${suffix}`
}

function changeTone(value) {
  const n = Number(value)
  if (!Number.isFinite(n) || n === 0) return 'text-gray-400'
  return n > 0 ? 'text-[#EF5350]' : 'text-[#26A69A]'
}

function canvasAngle(degFromTop) {
  return (Number(degFromTop) - 90) * Math.PI / 180
}

function findSliceFromPointer(event, chart) {
  if (!chart?.slices?.length) return null
  const rect = event.currentTarget.getBoundingClientRect()
  const x = (event.clientX - rect.left) / rect.width * chart.width
  const y = (event.clientY - rect.top) / rect.height * chart.height
  const dx = x - chart.center_x
  const dy = y - chart.center_y
  const distance = Math.sqrt(dx * dx + dy * dy)
  if (distance > chart.radius + 24) return null

  const deg = Math.atan2(dy, dx) * 180 / Math.PI
  const relative = (deg + 90 + 360) % 360
  return chart.slices.find(slice => {
    const start = Number(slice.start_deg)
    const end = Number(slice.end_deg)
    if (start <= end) return relative >= start && relative < end
    return relative >= start || relative < end
  }) || null
}

function ChangeCard({ label, change }) {
  const available = change?.available
  return (
    <div className="min-w-[92px] flex-1 border border-[#1F2A36] bg-[#0A0F14] px-3 py-2">
      <div className="text-[10px] text-gray-600">{label}變化</div>
      <div className={`mt-1 text-sm font-mono font-semibold ${changeTone(change?.delta_pct_points)}`}>
        {available ? signed(change.delta_pct_points, 2, 'pp') : '尚無基準'}
      </div>
      <div className="mt-0.5 text-[9px] text-gray-600">
        {available ? `基準 ${fmtDate(change.baseline_date)}` : '累積快照後會自動顯示'}
      </div>
    </div>
  )
}

function InteractivePieChart({ summary, activeSector, onSelect }) {
  const canvasRef = useRef(null)
  const chart = summary?.chart || {}
  const slices = chart.slices || []
  const visibleLabels = slices.filter(s => Number(s.pct) >= 1.4)
  const activeSlice = slices.find(s => s.name === activeSector)
  const [bubble, setBubble] = useState(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !chart?.slices?.length) return

    const width = Number(chart.width) || 720
    const height = Number(chart.height) || 520
    const cxBase = Number(chart.center_x) || width / 2
    const cyBase = Number(chart.center_y) || height / 2
    const radius = Number(chart.radius) || 210

    if (canvas.width !== width) canvas.width = width
    if (canvas.height !== height) canvas.height = height

    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, width, height)

    ctx.save()
    ctx.shadowColor = 'rgba(0,0,0,0.45)'
    ctx.shadowBlur = 12
    ctx.shadowOffsetY = 5

    for (const slice of slices) {
      const isActive = slice.name === activeSector
      const mid = canvasAngle(slice.mid_deg)
      const offset = isActive ? 9 : 0
      const cx = cxBase + Math.cos(mid) * offset
      const cy = cyBase + Math.sin(mid) * offset
      let start = canvasAngle(slice.start_deg)
      let end = canvasAngle(slice.end_deg)
      if (end <= start) end += Math.PI * 2

      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.arc(cx, cy, radius, start, end, false)
      ctx.closePath()
      ctx.globalAlpha = activeSector && !isActive ? 0.58 : 1
      ctx.fillStyle = slice.color || '#607D8B'
      ctx.fill()
      ctx.globalAlpha = 1
      ctx.lineWidth = isActive ? 3 : 1.5
      ctx.strokeStyle = isActive ? '#FFFFFF' : '#0A0A0A'
      ctx.stroke()
    }

    ctx.restore()

    ctx.beginPath()
    ctx.arc(cxBase, cyBase, 76, 0, Math.PI * 2)
    ctx.fillStyle = '#080A0D'
    ctx.fill()
    ctx.lineWidth = 1.5
    ctx.strokeStyle = '#24313D'
    ctx.stroke()

    ctx.fillStyle = '#E5E7EB'
    ctx.font = '600 18px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('產業', cxBase, cyBase - 7)
    ctx.fillStyle = '#64748B'
    ctx.font = '12px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    ctx.fillText('總配置', cxBase, cyBase + 13)
  }, [activeSector, chart, slices])

  useEffect(() => {
    if (!activeSlice) return
    setBubble(prev => {
      if (prev?.name === activeSlice.name) return prev
      return {
        name: activeSlice.name,
        pct: activeSlice.pct,
        color: activeSlice.color,
        x: Number(activeSlice.label_x) * 100,
        y: Number(activeSlice.label_y) * 100,
      }
    })
  }, [activeSlice])

  const handleClick = (event) => {
    const slice = findSliceFromPointer(event, chart)
    if (!slice) return
    const rect = event.currentTarget.getBoundingClientRect()
    onSelect(slice.name)
    setBubble({
      name: slice.name,
      pct: slice.pct,
      color: slice.color,
      x: (event.clientX - rect.left) / rect.width * 100,
      y: (event.clientY - rect.top) / rect.height * 100,
    })
  }

  return (
    <div className="relative mx-auto w-full max-w-[720px]">
      <div
        className="relative aspect-[720/520] select-none"
        onClick={handleClick}
        role="application"
        aria-label="主動式ETF產業配置互動饼圖"
      >
        {slices.length ? (
          <canvas
            ref={canvasRef}
            className="absolute inset-0 h-full w-full cursor-pointer"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-gray-600">
            尚無可顯示的產業占比
          </div>
        )}

        {visibleLabels.map(slice => (
          <button
            key={slice.name}
            type="button"
            onClick={(event) => {
              event.stopPropagation()
              onSelect(slice.name)
              setBubble({
                name: slice.name,
                pct: slice.pct,
                color: slice.color,
                x: Number(slice.label_x) * 100,
                y: Number(slice.label_y) * 100,
              })
            }}
            className={`absolute max-w-[108px] -translate-x-1/2 -translate-y-1/2 rounded border px-1.5 py-0.5 text-[9px] leading-tight shadow-md transition-colors ${
              activeSector === slice.name
                ? 'border-white bg-[#111820] text-white'
                : 'border-[#263340] bg-[#081018]/85 text-gray-200 hover:border-gray-300'
            }`}
            style={{
              left: `${Number(slice.label_x) * 100}%`,
              top: `${Number(slice.label_y) * 100}%`,
            }}
            title={`${slice.name} ${fmt(slice.pct, 1)}%`}
          >
            <span className="block truncate">{slice.name}</span>
            <span className="block font-mono text-[9px]" style={{ color: slice.color }}>{fmt(slice.pct, 1)}%</span>
          </button>
        ))}

        {bubble && (
          <div
            className="pointer-events-none absolute z-20 min-w-[132px] -translate-x-1/2 -translate-y-[115%] rounded border border-white/40 bg-[#060A0E]/95 px-3 py-2 text-center shadow-xl"
            style={{ left: `${bubble.x}%`, top: `${bubble.y}%` }}
          >
            <div className="truncate text-xs font-semibold text-white">{bubble.name}</div>
            <div className="mt-0.5 font-mono text-[11px]" style={{ color: bubble.color }}>
              {fmt(bubble.pct, 2)}%
            </div>
          </div>
        )}
      </div>

      <div className="mt-2 grid grid-cols-2 gap-1.5 sm:grid-cols-3 xl:grid-cols-4">
        {slices.map(slice => (
          <button
            key={slice.name}
            type="button"
            onClick={() => {
              onSelect(slice.name)
              setBubble({
                name: slice.name,
                pct: slice.pct,
                color: slice.color,
                x: Number(slice.label_x) * 100,
                y: Number(slice.label_y) * 100,
              })
            }}
            className={`flex items-center gap-1.5 border px-2 py-1 text-left text-[10px] ${
              activeSector === slice.name
                ? 'border-cyan-400 bg-[#10202A] text-white'
                : 'border-[#18222C] bg-[#080C10] text-gray-400 hover:text-white'
            }`}
          >
            <span className="h-2.5 w-2.5 flex-shrink-0" style={{ backgroundColor: slice.color }} />
            <span className="min-w-0 flex-1 truncate">{slice.name}</span>
            <span className="font-mono text-gray-500">{fmt(slice.pct, 1)}%</span>
          </button>
        ))}
      </div>
    </div>
  )
}

export default function ActiveEtfPanel() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [activeSector, setActiveSector] = useState('')

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true)
    else setLoading(true)
    setError('')
    try {
      const res = await api.getEtfSectorSummary(refresh)
      setSummary(res)
    } catch (e) {
      setError(`主動式ETF產業資料載入失敗：${e.message}`)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { load(false) }, [load])

  const sectors = summary?.sectors || []
  useEffect(() => {
    if (!sectors.length) return
    if (!activeSector || !sectors.some(s => s.name === activeSector)) {
      setActiveSector(sectors[0].name)
    }
  }, [activeSector, sectors])

  const sector = useMemo(
    () => sectors.find(s => s.name === activeSector) || sectors[0],
    [activeSector, sectors],
  )

  return (
    <div className="flex h-full flex-col bg-[#0A0A0A] text-gray-300">
      <div className="flex flex-shrink-0 items-center gap-3 border-b border-[#1A1A1A] bg-[#0D0D0D] px-4 py-2">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-white">主動式ETF產業總配置</div>
          <div className="text-[10px] text-gray-600">
            前端 Canvas 互動饼圖，股票型主動式ETF等權彙整
            {summary?.date ? `，最新持股日 ${summary.date}` : ''}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {loading && <span className="text-[10px] text-blue-400">載入中...</span>}
          {refreshing && <span className="text-[10px] text-blue-400">更新中...</span>}
          {error && <span className="text-[10px] text-red-400">{error}</span>}
          <button
            type="button"
            onClick={() => load(true)}
            disabled={loading || refreshing}
            className="rounded border border-[#2A2A2A] px-2.5 py-1 text-[10px] text-gray-400 hover:border-[#3A3A3A] hover:text-white disabled:opacity-40"
          >
            重新整理
          </button>
        </div>
      </div>

      {!loading && !error && !sectors.length && (
        <div className="flex flex-1 items-center justify-center text-xs text-gray-600">
          目前沒有可彙整的股票型主動式ETF持股資料
        </div>
      )}

      {sectors.length > 0 && sector && (
        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className="grid grid-cols-1 gap-4 border-b border-[#1A1A1A] bg-[#080A0D] p-4 xl:grid-cols-[minmax(420px,620px)_1fr]">
            <div className="min-w-0">
              <InteractivePieChart summary={summary} activeSector={activeSector} onSelect={setActiveSector} />
            </div>

            <div className="min-w-0 border border-[#1A1A1A] bg-[#0B0D0F]">
              <div className="flex items-center gap-3 border-b border-[#1A1A1A] px-4 py-3">
                <span className="h-4 w-4 flex-shrink-0" style={{ backgroundColor: sector.color }} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-lg font-semibold text-white">{sector.name}</div>
                  <div className="text-[10px] text-gray-600">
                    {sector.etf_count} 檔ETF持有，{sector.stock_count} 檔公司，總產業占比
                    <span className="ml-1 font-mono text-[#FFA726]">{fmt(sector.pct, 2)}%</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-px border-b border-[#1A1A1A] bg-[#1A1A1A]">
                <div className="bg-[#0B0D0F] px-3 py-3">
                  <div className="text-[10px] text-gray-600">彙整權重</div>
                  <div className="mt-1 font-mono text-lg font-semibold text-white">{fmt(sector.total_weight, 2)}</div>
                </div>
                <div className="bg-[#0B0D0F] px-3 py-3">
                  <div className="text-[10px] text-gray-600">持股列數</div>
                  <div className="mt-1 font-mono text-lg font-semibold text-white">{sector.positions}</div>
                </div>
                <div className="bg-[#0B0D0F] px-3 py-3">
                  <div className="text-[10px] text-gray-600">前20公司</div>
                  <div className="mt-1 font-mono text-lg font-semibold text-white">{sector.stocks?.length || 0}</div>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 p-3">
                {Object.entries(CHANGE_LABELS).map(([key, label]) => (
                  <ChangeCard key={key} label={label} change={sector.changes?.[key]} />
                ))}
              </div>

              <div className="border-t border-[#1A1A1A] px-3 py-2 text-[10px] text-gray-600">
                變化值使用已累積的產業快照比較；尚無1週或1月基準時會先顯示「尚無基準」，後續每日刷新後自動累積。
              </div>
            </div>
          </div>

          <div className="px-4 py-3">
            <div className="mb-2 flex items-center gap-3">
              <div className="text-sm font-semibold text-white">{sector.name} 前20公司彙總</div>
              <div className="text-[10px] text-gray-600">
                統計該產業中各公司被哪些主動式ETF投資，以及在該產業內的彙總占比
              </div>
            </div>

            <div className="min-w-[880px] overflow-hidden border border-[#1A1A1A]">
              <div className="grid grid-cols-[44px_86px_minmax(150px,1fr)_94px_100px_76px_minmax(260px,1.8fr)] gap-2 border-b border-[#1A1A1A] bg-[#101214] px-3 py-2 text-[10px] font-semibold text-gray-500">
                <div>#</div>
                <div>代號</div>
                <div>公司</div>
                <div className="text-right">產業內占比</div>
                <div className="text-right">彙整權重</div>
                <div className="text-right">ETF數</div>
                <div>投資的主動ETF</div>
              </div>
              <div className="divide-y divide-[#111]">
                {(sector.stocks || []).map((stock, index) => (
                  <div
                    key={stock.stock_code || `${stock.stock_name}-${index}`}
                    className="grid grid-cols-[44px_86px_minmax(150px,1fr)_94px_100px_76px_minmax(260px,1.8fr)] gap-2 px-3 py-2.5 text-[11px] odd:bg-[#080B0E] even:bg-[#060708] hover:bg-[#0F1620]"
                  >
                    <div className="font-mono text-gray-600">{index + 1}</div>
                    <div className="font-mono font-semibold text-[#40C4FF]">{stock.stock_code}</div>
                    <div className="truncate text-gray-200">{stock.stock_name}</div>
                    <div className="text-right font-mono text-[#FFA726]">{fmt(stock.sector_pct, 2)}%</div>
                    <div className="text-right font-mono text-gray-300">{fmt(stock.total_weight, 2)}</div>
                    <div className="text-right text-gray-500">{stock.etf_count}</div>
                    <div className="flex flex-wrap gap-1">
                      {(stock.etfs || []).map(etf => (
                        <span
                          key={`${stock.stock_code}-${etf.code}`}
                          title={etf.name}
                          className="rounded border border-[#1F2A36] bg-[#0E1720] px-1.5 py-0.5 text-[9px] text-gray-300"
                        >
                          <span className="font-mono text-cyan-300">{etf.code}</span>
                          <span className="ml-1 font-mono text-gray-500">{fmt(etf.weight, 2)}%</span>
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-2 text-[10px] text-gray-700">
              {summary.method}
              {summary.errors?.length ? `；${summary.errors.length} 檔ETF暫時無法載入，已排除於彙整。` : ''}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
