import { useEffect, useRef, useState, useCallback } from 'react'
import { createChart, CrosshairMode, LineStyle } from 'lightweight-charts'
import { api } from '../api/stocks.js'

const CHART_BG = '#0D0D0D'
const GRID_COLOR = '#1A1A1A'
const TEXT_COLOR = '#7A7A7A'
const BORDER_COLOR = '#2A2A2A'

const MA_STYLES = {
  MA5:   { color: '#FF6D00', lineWidth: 1 },
  MA10:  { color: '#FFD600', lineWidth: 1 },
  MA20:  { color: '#40C4FF', lineWidth: 1 },
  MA60:  { color: '#1565C0', lineWidth: 1 },
  MA120: { color: '#AB47BC', lineWidth: 1 },
  MA240: { color: '#EC407A', lineWidth: 1 },
}

const baseChartOptions = (height) => ({
  layout: {
    background: { color: CHART_BG },
    textColor: TEXT_COLOR,
    fontSize: 11,
  },
  grid: {
    vertLines: { color: GRID_COLOR },
    horzLines: { color: GRID_COLOR },
  },
  crosshair: { mode: CrosshairMode.Normal },
  rightPriceScale: { borderColor: BORDER_COLOR },
  timeScale: {
    borderColor: BORDER_COLOR,
    timeVisible: true,
    secondsVisible: false,
  },
  handleScale: true,
  handleScroll: true,
  height,
})

// Prevent sync loops
let syncing = false

function syncLogicalRange(source, targets) {
  source.timeScale().subscribeVisibleLogicalRangeChange(range => {
    if (syncing || !range) return
    syncing = true
    targets.forEach(t => t.timeScale().setVisibleLogicalRange(range))
    syncing = false
  })
}

export default function StockChart({ symbol, stockName, interval }) {
  const mainRef    = useRef(null)
  const volRef     = useRef(null)
  const rsiRef     = useRef(null)
  const kdRef      = useRef(null)
  const chartsRef  = useRef(null)
  const seriesRef  = useRef(null)

  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)
  const [visibleMAs, setVisibleMAs] = useState(
    { MA5: true, MA10: true, MA20: true, MA60: true, MA120: false, MA240: false }
  )
  const [showBB, setShowBB] = useState(true)
  const [ohlcInfo, setOhlcInfo] = useState(null)

  // ── Initialize charts (once) ──────────────────────────────────────────────
  useEffect(() => {
    if (!mainRef.current) return

    const main = createChart(mainRef.current, baseChartOptions(380))
    const vol  = createChart(volRef.current,  { ...baseChartOptions(75), rightPriceScale: { visible: false, borderColor: BORDER_COLOR } })
    const rsi  = createChart(rsiRef.current,  { ...baseChartOptions(75) })
    const kd   = createChart(kdRef.current,   { ...baseChartOptions(75) })

    // Candlestick
    const candle = main.addCandlestickSeries({
      upColor: '#EF5350', downColor: '#26A69A',
      borderUpColor: '#EF5350', borderDownColor: '#26A69A',
      wickUpColor: '#EF5350', wickDownColor: '#26A69A',
    })

    // MA lines
    const maSeries = {}
    for (const [key, style] of Object.entries(MA_STYLES)) {
      maSeries[key] = main.addLineSeries({ ...style, lastValueVisible: false, priceLineVisible: false })
    }

    // Bollinger Bands
    const bbUpper = main.addLineSeries({
      color: '#546E7A', lineWidth: 1, lineStyle: LineStyle.Dashed,
      lastValueVisible: false, priceLineVisible: false,
    })
    const bbMiddle = main.addLineSeries({
      color: '#546E7A', lineWidth: 1,
      lastValueVisible: false, priceLineVisible: false,
    })
    const bbLower = main.addLineSeries({
      color: '#546E7A', lineWidth: 1, lineStyle: LineStyle.Dashed,
      lastValueVisible: false, priceLineVisible: false,
    })

    // Volume
    const volume = vol.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      scaleMargins: { top: 0.1, bottom: 0 },
    })
    vol.priceScale('').applyOptions({ scaleMargins: { top: 0.1, bottom: 0 } })

    // RSI
    const rsiLine = rsi.addLineSeries({ color: '#FF9800', lineWidth: 1, lastValueVisible: true, priceLineVisible: false })
    const rsi70   = rsi.addLineSeries({ color: '#EF5350', lineWidth: 1, lineStyle: LineStyle.Dashed, lastValueVisible: false, priceLineVisible: false })
    const rsi30   = rsi.addLineSeries({ color: '#26A69A', lineWidth: 1, lineStyle: LineStyle.Dashed, lastValueVisible: false, priceLineVisible: false })
    rsi.priceScale('right').applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } })

    // KD
    const kLine = kd.addLineSeries({ color: '#4CAF50', lineWidth: 1, lastValueVisible: true, priceLineVisible: false })
    const dLine = kd.addLineSeries({ color: '#F44336', lineWidth: 1, lastValueVisible: true, priceLineVisible: false })
    const kd80  = kd.addLineSeries({ color: '#EF535066', lineWidth: 1, lineStyle: LineStyle.Dashed, lastValueVisible: false, priceLineVisible: false })
    const kd20  = kd.addLineSeries({ color: '#26A69A66', lineWidth: 1, lineStyle: LineStyle.Dashed, lastValueVisible: false, priceLineVisible: false })
    kd.priceScale('right').applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } })

    // Crosshair info
    main.subscribeCrosshairMove(param => {
      if (!param.time || !param.seriesData) return
      const d = param.seriesData.get(candle)
      if (d) setOhlcInfo(d)
    })

    // Time scale sync: all four charts drive each other
    syncLogicalRange(main, [vol, rsi, kd])
    syncLogicalRange(vol,  [main, rsi, kd])
    syncLogicalRange(rsi,  [main, vol, kd])
    syncLogicalRange(kd,   [main, vol, rsi])

    // Resize observer
    const ro = new ResizeObserver(() => {
      const w = mainRef.current?.clientWidth || 600
      main.resize(w, 380)
      vol.resize(w, 75)
      rsi.resize(w, 75)
      kd.resize(w, 75)
    })
    ro.observe(mainRef.current)

    chartsRef.current = { main, vol, rsi, kd }
    seriesRef.current = { candle, maSeries, bbUpper, bbMiddle, bbLower, volume, rsiLine, rsi70, rsi30, kLine, dLine, kd80, kd20 }

    return () => {
      ro.disconnect()
      main.remove(); vol.remove(); rsi.remove(); kd.remove()
    }
  }, [])

  // ── Load data ─────────────────────────────────────────────────────────────
  const loadData = useCallback(async () => {
    if (!seriesRef.current || !symbol) return
    setLoading(true)
    setError(null)
    try {
      const data = await api.getKline(symbol, interval)
      const { candle, maSeries, bbUpper, bbMiddle, bbLower, volume, rsiLine, rsi70, rsi30, kLine, dLine, kd80, kd20 } = seriesRef.current

      candle.setData(data.data.map(d => ({
        time: d.time, open: d.open, high: d.high, low: d.low, close: d.close,
      })))

      volume.setData(data.data.map(d => ({
        time: d.time,
        value: d.volume,
        color: d.close >= d.open ? '#EF535055' : '#26A69A55',
      })))

      for (const key of Object.keys(MA_STYLES)) {
        maSeries[key].setData(data.indicators[key] || [])
      }

      bbUpper.setData(data.indicators.BB_upper || [])
      bbMiddle.setData(data.indicators.BB_middle || [])
      bbLower.setData(data.indicators.BB_lower || [])

      const rsiData = data.indicators.RSI || []
      rsiLine.setData(rsiData)
      const times = rsiData.map(d => d.time)
      rsi70.setData(times.map(t => ({ time: t, value: 70 })))
      rsi30.setData(times.map(t => ({ time: t, value: 30 })))

      const kData = data.indicators.K || []
      const dData = data.indicators.D || []
      kLine.setData(kData)
      dLine.setData(dData)
      const kdTimes = kData.map(d => d.time)
      kd80.setData(kdTimes.map(t => ({ time: t, value: 80 })))
      kd20.setData(kdTimes.map(t => ({ time: t, value: 20 })))

      chartsRef.current.main.timeScale().fitContent()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [symbol, interval])

  useEffect(() => { loadData() }, [loadData])

  // ── Toggle MA visibility ──────────────────────────────────────────────────
  useEffect(() => {
    if (!seriesRef.current) return
    for (const [key, visible] of Object.entries(visibleMAs)) {
      seriesRef.current.maSeries[key]?.applyOptions({ visible })
    }
  }, [visibleMAs])

  useEffect(() => {
    if (!seriesRef.current) return
    const { bbUpper, bbMiddle, bbLower } = seriesRef.current
    bbUpper.applyOptions({ visible: showBB })
    bbMiddle.applyOptions({ visible: showBB })
    bbLower.applyOptions({ visible: showBB })
  }, [showBB])

  const toggleMA = (key) => setVisibleMAs(v => ({ ...v, [key]: !v[key] }))

  return (
    <div className="flex flex-col h-full bg-[#0D0D0D] select-none">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-[#2A2A2A] bg-[#0A0A0A] flex-shrink-0 flex-wrap">
        <span className="text-white font-semibold text-sm">{symbol}</span>
        <span className="text-gray-500 text-xs">{stockName}</span>

        {/* OHLCV info on crosshair */}
        {ohlcInfo && (
          <div className="flex gap-2 text-[10px] font-mono ml-2">
            <span className="text-gray-500">O <span className="text-white">{ohlcInfo.open?.toFixed(2)}</span></span>
            <span className="text-gray-500">H <span className="text-[#EF5350]">{ohlcInfo.high?.toFixed(2)}</span></span>
            <span className="text-gray-500">L <span className="text-[#26A69A]">{ohlcInfo.low?.toFixed(2)}</span></span>
            <span className="text-gray-500">C <span className={ohlcInfo.close >= ohlcInfo.open ? 'text-[#EF5350]' : 'text-[#26A69A]'}>{ohlcInfo.close?.toFixed(2)}</span></span>
          </div>
        )}

        <div className="ml-auto flex items-center gap-1 flex-wrap">
          {/* MA toggles */}
          {Object.entries(MA_STYLES).map(([key, style]) => (
            <button
              key={key}
              onClick={() => toggleMA(key)}
              className={`px-1.5 py-0.5 rounded text-[10px] border transition-opacity ${
                visibleMAs[key] ? 'opacity-100' : 'opacity-30'
              }`}
              style={{ borderColor: style.color, color: style.color }}
            >
              {key}
            </button>
          ))}
          <button
            onClick={() => setShowBB(v => !v)}
            className={`px-1.5 py-0.5 rounded text-[10px] border border-[#546E7A] text-[#546E7A] transition-opacity ${showBB ? 'opacity-100' : 'opacity-30'}`}
          >
            BB
          </button>
          <button
            onClick={() => loadData()}
            className="px-2 py-0.5 rounded text-[10px] border border-[#2A2A2A] text-gray-400 hover:text-white ml-1"
            title="重新整理"
          >
            ↻
          </button>
        </div>
      </div>

      {loading && (
        <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
          <span className="text-gray-400 text-sm">載入中...</span>
        </div>
      )}
      {error && (
        <div className="px-4 py-2 text-red-400 text-xs bg-[#1A0000]">{error}</div>
      )}

      {/* Charts stacked */}
      <div className="flex-1 flex flex-col min-h-0 relative overflow-y-auto">
        <div ref={mainRef} className="w-full flex-shrink-0" style={{ height: 380 }} />

        <div className="px-3 pt-1 flex-shrink-0">
          <span className="text-[10px] text-gray-600">成交量</span>
        </div>
        <div ref={volRef} className="w-full flex-shrink-0" style={{ height: 75 }} />

        <div className="px-3 pt-1 flex-shrink-0 flex items-center gap-2">
          <span className="text-[10px] text-gray-600">RSI (14)</span>
          <span className="text-[10px] text-[#EF5350]">── 70</span>
          <span className="text-[10px] text-[#26A69A]">── 30</span>
        </div>
        <div ref={rsiRef} className="w-full flex-shrink-0" style={{ height: 75 }} />

        <div className="px-3 pt-1 flex-shrink-0 flex items-center gap-2">
          <span className="text-[10px] text-gray-600">KD (9,3,3)</span>
          <span className="text-[10px] text-[#4CAF50]">── K</span>
          <span className="text-[10px] text-[#F44336]">── D</span>
        </div>
        <div ref={kdRef} className="w-full flex-shrink-0" style={{ height: 75 }} />
      </div>
    </div>
  )
}
