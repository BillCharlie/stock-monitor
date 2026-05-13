import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api/stocks.js'

const SECTOR_COLORS = {
  '半導體': '#40C4FF',
  '科技系統廠': '#26A69A',
  '電子零組件': '#80DEEA',
  '其他電子': '#90A4AE',
  '通信網路': '#64B5F6',
  '鋼鐵': '#A1887F',
  '電機機械': '#A5D6A7',
  '電器電纜': '#FFCC80',
  '太陽能/綠能': '#FFF176',
  'AI與雲端': '#7E57C2',
  '金融': '#CE93D8',
  '光學': '#80CBC4',
  '化工/塑化': '#FF7043',
  '生技醫療': '#B39DDB',
  '航運': '#4DD0E1',
  '零售': '#F48FB1',
  '汽車': '#FFCC80',
  '水泥': '#BCAAA4',
  '食品': '#E6EE9C',
  '建設': '#CFD8DC',
  '紡織': '#FFAB91',
  '傳產': '#90A4AE',
  '其他': '#37474F',
}

const FALLBACK_COLORS = [
  '#40C4FF', '#26A69A', '#FF9800', '#CE93D8', '#FFF176', '#80DEEA',
  '#A1887F', '#B39DDB', '#FF7043', '#90A4AE', '#66BB6A', '#F48FB1',
]

function sectorColor(name, index = 0) {
  return SECTOR_COLORS[name] || FALLBACK_COLORS[index % FALLBACK_COLORS.length]
}

function fmt(value, digits = 1) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '0'
  return n.toFixed(digits)
}

function fmtDate(value) {
  if (!value) return ''
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

function SvgPieChart({ slices, size = 220 }) {
  const total = slices.reduce((sum, s) => sum + s.value, 0)
  if (!total) return null

  const cx = size / 2
  const cy = size / 2
  const radius = size * 0.42
  let angle = -Math.PI / 2

  const paths = slices.filter(s => s.value > 0).map(slice => {
    const span = (slice.value / total) * Math.PI * 2
    const end = angle + span
    const x1 = cx + radius * Math.cos(angle)
    const y1 = cy + radius * Math.sin(angle)
    const x2 = cx + radius * Math.cos(end)
    const y2 = cy + radius * Math.sin(end)
    const large = span > Math.PI ? 1 : 0
    const d = `M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2} Z`
    angle = end
    return { ...slice, d, pct: slice.value / total * 100 }
  })

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="block">
      {paths.map((p, index) => (
        <path key={`${p.label}-${index}`} d={p.d} fill={p.color} stroke="#0A0A0A" strokeWidth="1.5">
          <title>{p.label}: {fmt(p.pct)}%</title>
        </path>
      ))}
      <circle cx={cx} cy={cy} r={size * 0.22} fill="#0A0A0A" stroke="#1E2833" strokeWidth="1" />
      <text x={cx} y={cy - 4} textAnchor="middle" className="fill-gray-300 text-[13px] font-semibold">產業</text>
      <text x={cx} y={cy + 13} textAnchor="middle" className="fill-gray-600 text-[10px]">ETF彙整</text>
    </svg>
  )
}

function buildModel(allData) {
  const entries = Object.entries(allData || {})
  const stockEtfs = entries
    .filter(([code, info]) => !code.endsWith('D') && info && !info.error && info.holdings?.length)
    .map(([code, info]) => [code, info])

  const sectorMap = new Map()
  const etfSummaries = []
  let latestDate = ''
  let totalPositions = 0

  for (const [etfCode, etf] of stockEtfs) {
    const sectorWeights = {}
    const holdings = etf.holdings || []
    totalPositions += holdings.length
    if (etf.date && (!latestDate || etf.date > latestDate)) latestDate = etf.date

    for (const holding of holdings) {
      const weight = Number(holding.weight_pct) || 0
      if (weight <= 0) continue
      const sector = holding.sector || '其他'
      const color = sectorColor(sector, sectorMap.size)

      if (!sectorMap.has(sector)) {
        sectorMap.set(sector, {
          name: sector,
          color,
          totalWeight: 0,
          positions: 0,
          etfCodes: new Set(),
          stocks: new Map(),
        })
      }

      const sec = sectorMap.get(sector)
      sec.totalWeight += weight
      sec.positions += 1
      sec.etfCodes.add(etfCode)
      sectorWeights[sector] = (sectorWeights[sector] || 0) + weight

      const stockCode = holding.stock_code || holding.stock_name || 'UNKNOWN'
      if (!sec.stocks.has(stockCode)) {
        sec.stocks.set(stockCode, {
          code: stockCode,
          name: holding.stock_name || stockCode,
          totalWeight: 0,
          etfs: [],
        })
      }
      const stock = sec.stocks.get(stockCode)
      stock.totalWeight += weight
      stock.etfs.push({
        code: etfCode,
        name: etf.name || etfCode,
        weight,
      })
    }

    const topSectors = Object.entries(sectorWeights)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3)
      .map(([name, weight]) => ({ name, weight }))

    etfSummaries.push({
      code: etfCode,
      name: etf.name || etfCode,
      date: etf.date,
      holdings: holdings.length,
      top10Weight: etf.top10_weight,
      topSectors,
      topHoldings: holdings.slice(0, 5),
    })
  }

  const totalWeight = Array.from(sectorMap.values()).reduce((sum, s) => sum + s.totalWeight, 0)
  const sectors = Array.from(sectorMap.values())
    .sort((a, b) => b.totalWeight - a.totalWeight)
    .map((sector, index) => ({
      ...sector,
      color: sectorColor(sector.name, index),
      pct: totalWeight ? sector.totalWeight / totalWeight * 100 : 0,
      etfCount: sector.etfCodes.size,
      stocks: Array.from(sector.stocks.values())
        .sort((a, b) => b.totalWeight - a.totalWeight)
        .map(stock => ({
          ...stock,
          etfs: stock.etfs.sort((a, b) => b.weight - a.weight),
        })),
    }))

  return {
    sectors,
    etfSummaries: etfSummaries.sort((a, b) => a.code.localeCompare(b.code)),
    latestDate,
    stockEtfCount: stockEtfs.length,
    totalPositions,
    totalWeight,
    errors: entries.filter(([, info]) => info?.error).map(([code, info]) => ({ code, error: info.error })),
  }
}

export default function ActiveEtfPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [activeSector, setActiveSector] = useState('')

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true)
    else setLoading(true)
    setError('')
    try {
      const res = await api.getAllEtfHoldings(refresh)
      setData(res)
    } catch (e) {
      setError('主動式ETF資料載入失敗：' + e.message)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { load(false) }, [load])

  const model = useMemo(() => buildModel(data), [data])

  useEffect(() => {
    if (!model.sectors.length) return
    if (!activeSector || !model.sectors.some(s => s.name === activeSector)) {
      setActiveSector(model.sectors[0].name)
    }
  }, [activeSector, model.sectors])

  const sector = model.sectors.find(s => s.name === activeSector) || model.sectors[0]
  const pieSlices = model.sectors.slice(0, 12).map(s => ({
    label: s.name,
    value: s.totalWeight,
    color: s.color,
  }))

  return (
    <div className="flex flex-col h-full bg-[#0A0A0A] text-gray-300">
      <div className="flex-shrink-0 flex items-center gap-3 px-4 py-2 border-b border-[#1A1A1A] bg-[#0D0D0D]">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-white">主動式ETF產業配置</div>
          <div className="text-[10px] text-gray-600">
            股票型主動式ETF等權彙整{model.latestDate ? `，最新持股日 ${model.latestDate}` : ''}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {loading && <span className="text-[10px] text-blue-400">載入中...</span>}
          {refreshing && <span className="text-[10px] text-blue-400">更新中...</span>}
          {error && <span className="text-[10px] text-red-400">{error}</span>}
          <button
            onClick={() => load(true)}
            disabled={loading || refreshing}
            className="px-2.5 py-1 text-[10px] rounded border border-[#2A2A2A] text-gray-400 hover:text-white hover:border-[#3A3A3A] disabled:opacity-40"
          >
            重新整理
          </button>
        </div>
      </div>

      {!loading && !error && model.sectors.length === 0 && (
        <div className="flex-1 flex items-center justify-center text-xs text-gray-600">
          目前沒有可彙整的股票型主動式ETF持股資料
        </div>
      )}

      {model.sectors.length > 0 && (
        <div className="flex-1 min-h-0 grid grid-cols-1 xl:grid-cols-[320px_1fr]">
          <div className="min-h-0 border-r border-[#1A1A1A] bg-[#0B0D0F] flex flex-col">
            <div className="px-4 py-3 border-b border-[#1A1A1A]">
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="text-lg font-semibold text-white">{model.stockEtfCount}</div>
                  <div className="text-[9px] text-gray-600">股票型ETF</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-white">{model.sectors.length}</div>
                  <div className="text-[9px] text-gray-600">產業</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-white">{model.totalPositions}</div>
                  <div className="text-[9px] text-gray-600">持股列數</div>
                </div>
              </div>
            </div>

            <div className="px-4 py-3 flex justify-center border-b border-[#1A1A1A]">
              <SvgPieChart slices={pieSlices} />
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto">
              {model.sectors.map(s => (
                <button
                  key={s.name}
                  onClick={() => setActiveSector(s.name)}
                  className={`w-full px-3 py-2 border-b border-[#111] text-left hover:bg-[#121820] ${
                    activeSector === s.name ? 'bg-[#101820]' : ''
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: s.color }} />
                    <span className="text-[11px] text-gray-100 truncate">{s.name}</span>
                    <span className="ml-auto text-[10px] font-mono text-gray-400">{fmt(s.pct)}%</span>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[9px] text-gray-600">
                    <span>{s.etfCount} 檔ETF</span>
                    <span>{s.stocks.length} 檔成分</span>
                    <span className="ml-auto">{fmt(s.totalWeight, 2)} 權重</span>
                  </div>
                  <div className="mt-1 h-1.5 bg-[#1A1A1A] rounded overflow-hidden">
                    <div className="h-full rounded" style={{ width: `${Math.min(100, s.pct)}%`, backgroundColor: s.color }} />
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="min-h-0 overflow-y-auto">
            <div className="px-4 py-3 border-b border-[#1A1A1A] bg-[#0D0D0D]">
              <div className="flex flex-wrap items-center gap-2">
                <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: sector.color }} />
                <span className="text-base font-semibold text-white">{sector.name}</span>
                <span className="text-[10px] text-gray-600">
                  {sector.etfCount} 檔ETF持有，{sector.stocks.length} 檔成分，彙整占比 {fmt(sector.pct)}%
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 2xl:grid-cols-[1fr_360px] min-h-0">
              <div className="min-w-0">
                <div className="sticky top-0 z-10 grid grid-cols-[54px_minmax(120px,1fr)_90px_110px_minmax(180px,1.4fr)] gap-2 px-4 py-2 bg-[#101214] border-b border-[#1A1A1A] text-[10px] text-gray-600">
                  <span>代號</span>
                  <span>公司</span>
                  <span className="text-right">累計占比</span>
                  <span className="text-right">ETF數</span>
                  <span>各ETF占比</span>
                </div>
                {sector.stocks.map(stock => (
                  <div
                    key={stock.code}
                    className="grid grid-cols-[54px_minmax(120px,1fr)_90px_110px_minmax(180px,1.4fr)] gap-2 px-4 py-2 border-b border-[#111] hover:bg-[#101214] text-[11px]"
                  >
                    <span className="font-mono text-[#40C4FF]">{stock.code}</span>
                    <span className="truncate text-gray-200">{stock.name}</span>
                    <span className="font-mono text-[#FFA726] text-right">{fmt(stock.totalWeight, 2)}%</span>
                    <span className="text-right text-gray-500">{stock.etfs.length}</span>
                    <span className="flex flex-wrap gap-1">
                      {stock.etfs.map(etf => (
                        <span
                          key={`${stock.code}-${etf.code}`}
                          title={etf.name}
                          className="text-[9px] px-1.5 py-0.5 rounded bg-[#111820] border border-[#1F2A36] text-gray-300"
                        >
                          {etf.code} {fmt(etf.weight, 2)}%
                        </span>
                      ))}
                    </span>
                  </div>
                ))}
              </div>

              <div className="border-l border-[#1A1A1A] bg-[#0B0D0F]">
                <div className="px-3 py-2 text-[11px] font-semibold text-gray-200 border-b border-[#1A1A1A]">
                  ETF投資摘要
                </div>
                <div className="max-h-[520px] overflow-y-auto">
                  {model.etfSummaries.map(etf => (
                    <div key={etf.code} className="px-3 py-2 border-b border-[#111]">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[11px] text-[#40C4FF]">{etf.code}</span>
                        <span className="text-[11px] text-gray-200 truncate">{etf.name}</span>
                        <span className="ml-auto text-[9px] text-gray-600">{fmtDate(etf.date)}</span>
                      </div>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {etf.topSectors.map(s => (
                          <span key={`${etf.code}-${s.name}`} className="text-[9px] text-gray-500">
                            {s.name} {fmt(s.weight, 1)}%
                          </span>
                        ))}
                      </div>
                      <div className="mt-1 text-[9px] text-gray-700">
                        前五大：{etf.topHoldings.map(h => `${h.stock_code || h.stock_name} ${fmt(h.weight_pct, 1)}%`).join(' / ')}
                      </div>
                    </div>
                  ))}
                </div>
                {model.errors.length > 0 && (
                  <div className="px-3 py-2 border-t border-[#1A1A1A] text-[9px] text-yellow-600">
                    {model.errors.length} 檔ETF暫時無法載入，已排除於彙整。
                  </div>
                )}
              </div>
            </div>

            <div className="px-4 py-2 text-[10px] text-gray-700 border-t border-[#1A1A1A]">
              彙整方式：將各股票型主動式ETF揭露的持股權重直接加總後換算比例，未依ETF規模加權。
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
