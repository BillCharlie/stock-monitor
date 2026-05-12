import { useEffect, useRef, useState } from 'react'
import MarketOverview from './components/MarketOverview.jsx'
import WatchlistPanel from './components/WatchlistPanel.jsx'
import StockChart from './components/StockChart.jsx'
import AnalysisPanel from './components/AnalysisPanel.jsx'
import NewsPanel from './components/NewsPanel.jsx'
import TrumpNewsPanel from './components/TrumpNewsPanel.jsx'
import AccessKeyPanel from './components/AccessKeyPanel.jsx'
import { api, keys } from './api/stocks.js'

export default function App() {
  const [selected, setSelected] = useState({ symbol: '2330.TW', name: '台積電' })
  const [interval, setInterval] = useState('1d')
  const [activeTab, setActiveTab] = useState('chart')
  const [generating, setGenerating] = useState(false)
  const [reportMsg, setReportMsg] = useState('')
  const [hasPdf, setHasPdf] = useState(false)
  const [showKeys, setShowKeys] = useState(false)
  const [sidebarW, setSidebarW] = useState(224)
  const resizingRef = useRef(false)
  const resizeStartXRef = useRef(0)
  const resizeStartWRef = useRef(0)

  useEffect(() => {
    const onMove = (e) => {
      if (!resizingRef.current) return
      const delta = e.clientX - resizeStartXRef.current
      setSidebarW(Math.max(160, Math.min(480, resizeStartWRef.current + delta)))
    }
    const onUp = () => {
      if (resizingRef.current) {
        document.body.style.userSelect = ''
        document.body.style.cursor = ''
      }
      resizingRef.current = false
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [])

  const handleResizeMouseDown = (e) => {
    e.preventDefault()
    resizingRef.current = true
    resizeStartXRef.current = e.clientX
    resizeStartWRef.current = sidebarW
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'col-resize'
  }

  // Show key indicator: lock icon is green if both keys are set, yellow if partial, gray if none
  const hasReportKey = keys.hasReport()
  const hasStockKey  = keys.hasStock()
  const keyStatus = hasReportKey && hasStockKey ? 'both'
    : hasReportKey || hasStockKey ? 'partial' : 'none'

  const handleGenerate = async () => {
    if (!keys.getReport()) {
      setShowKeys(true)
      setReportMsg('請先設定報告生成密鑰')
      return
    }
    setGenerating(true)
    setReportMsg('分析中，請稍候（約1-2分鐘）...')
    try {
      const res = await api.triggerGptReport()
      const ok  = res.email_sent ? ' ✉ 已發送Email' : ''
      const pdf = res.pdf_saved  ? ' PDF已儲存' : ''
      setReportMsg(`報告生成完成${ok}${pdf}`)
      setHasPdf(!!res.pdf_saved)
      setActiveTab('report')
    } catch (e) {
      if (e.message.includes('401') || e.message.includes('密鑰')) {
        setReportMsg('密鑰錯誤，請重新設定')
        setShowKeys(true)
      } else {
        setReportMsg('生成失敗：' + e.message)
      }
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="flex flex-col h-screen bg-[#0D0D0D] overflow-hidden">
      <MarketOverview />

      <div className="flex flex-1 min-h-0">
        <div style={{ width: sidebarW }} className="relative flex-shrink-0 border-r border-[#2A2A2A]">
          <WatchlistPanel
            onSelect={(symbol, name) => {
              setSelected({ symbol, name })
              setActiveTab('chart')
            }}
            selectedSymbol={selected.symbol}
            onNeedKey={() => setShowKeys(true)}
          />
          <div
            className="absolute right-0 top-0 w-1.5 h-full cursor-col-resize hover:bg-blue-500/20 active:bg-blue-500/40 z-10"
            onMouseDown={handleResizeMouseDown}
          />
        </div>

        <div className="flex flex-col flex-1 min-w-0">
          {/* Tab bar */}
          <div className="flex items-center gap-1 px-3 py-2 border-b border-[#2A2A2A] bg-[#141414] flex-shrink-0">
            {[
              { id: 'chart',    label: 'K線圖' },
              { id: 'analysis', label: '個股分析' },
              { id: 'report',   label: '每日報告' },
              { id: 'news',     label: '消息面' },
              { id: 'trumpNews', label: 'TrumpNews' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1 rounded text-xs transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-700 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-[#2A2A2A]'
                }`}
              >
                {tab.label}
              </button>
            ))}

            {activeTab === 'chart' && (
              <div className="flex gap-1 ml-4">
                {[
                  { val: '1d', label: '日K' },
                  { val: '1wk', label: '週K' },
                  { val: '1mo', label: '月K' },
                ].map(iv => (
                  <button
                    key={iv.val}
                    onClick={() => setInterval(iv.val)}
                    className={`px-2 py-1 rounded text-xs ${
                      interval === iv.val
                        ? 'bg-[#1565C0] text-white'
                        : 'text-gray-500 hover:text-white border border-[#2A2A2A]'
                    }`}
                  >
                    {iv.label}
                  </button>
                ))}
              </div>
            )}

            <div className="ml-auto flex items-center gap-2">
              {reportMsg && (
                <span className={`text-xs ${reportMsg.includes('失敗') || reportMsg.includes('錯誤') ? 'text-red-400' : 'text-green-400'}`}>
                  {reportMsg}
                </span>
              )}

              {hasPdf && (
                <a
                  href={api.downloadPdfUrl()}
                  target="_blank"
                  rel="noreferrer"
                  className="px-3 py-1 text-xs bg-[#1A237E] hover:bg-[#283593] text-blue-300 rounded transition-colors"
                >
                  下載PDF
                </a>
              )}

              <button
                onClick={handleGenerate}
                disabled={generating}
                className="px-3 py-1 text-xs bg-[#1B5E20] hover:bg-[#2E7D32] text-green-300 rounded disabled:opacity-50 transition-colors"
              >
                {generating ? '生成中...' : '生成每日報告'}
              </button>

              {/* Key settings button */}
              <button
                onClick={() => setShowKeys(true)}
                title="設定存取密鑰"
                className={`w-7 h-7 rounded flex items-center justify-center text-sm transition-colors border ${
                  keyStatus === 'both'    ? 'border-green-700 text-green-400 hover:bg-green-900/30' :
                  keyStatus === 'partial' ? 'border-yellow-700 text-yellow-400 hover:bg-yellow-900/30' :
                                           'border-[#333] text-gray-500 hover:text-white hover:border-gray-500'
                }`}
              >
                {keyStatus === 'none' ? '🔒' : '🔑'}
              </button>
            </div>
          </div>

          <div className="flex-1 min-h-0 overflow-hidden">
            {activeTab === 'chart' && (
              <StockChart symbol={selected.symbol} stockName={selected.name} interval={interval} />
            )}
            {activeTab === 'analysis' && (
              <AnalysisPanel symbol={selected.symbol} stockName={selected.name} mode="single" />
            )}
            {activeTab === 'report' && (
              <AnalysisPanel symbol={selected.symbol} stockName={selected.name} mode="report" />
            )}
            {activeTab === 'news' && (
              <NewsPanel onNeedKey={() => setShowKeys(true)} />
            )}
            {activeTab === 'trumpNews' && (
              <TrumpNewsPanel onNeedKey={() => setShowKeys(true)} />
            )}
          </div>
        </div>
      </div>

      {showKeys && <AccessKeyPanel onClose={() => setShowKeys(false)} />}
    </div>
  )
}
