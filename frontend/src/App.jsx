import { useEffect, useState } from 'react'
import MarketOverview from './components/MarketOverview.jsx'
import WatchlistPanel from './components/WatchlistPanel.jsx'
import StockChart from './components/StockChart.jsx'
import AnalysisPanel from './components/AnalysisPanel.jsx'
import { api } from './api/stocks.js'

export default function App() {
  const [selected, setSelected] = useState({ symbol: '2330.TW', name: '台積電' })
  const [interval, setInterval] = useState('1d')
  const [activeTab, setActiveTab] = useState('chart') // 'chart' | 'analysis' | 'report'
  const [generating, setGenerating] = useState(false)
  const [reportMsg, setReportMsg] = useState('')

  const [hasPdf, setHasPdf] = useState(false)

  const handleGenerate = async () => {
    setGenerating(true)
    setReportMsg('分析中，請稍候（約1-2分鐘）...')
    try {
      const res = await api.triggerGptReport()
      const ok = res.email_sent ? '✉ 已發送Email' : ''
      const pdf = res.pdf_saved ? '  📄 PDF已儲存' : ''
      setReportMsg(`報告生成完成 ${ok}${pdf}`)
      setHasPdf(!!res.pdf_saved)
      setActiveTab('report')
    } catch (e) {
      setReportMsg('生成失敗：' + e.message)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="flex flex-col h-screen bg-[#0D0D0D] overflow-hidden">
      {/* Top bar: market overview */}
      <MarketOverview />

      {/* Main content */}
      <div className="flex flex-1 min-h-0">
        {/* Left: watchlist */}
        <div className="w-56 flex-shrink-0 border-r border-[#2A2A2A] overflow-y-auto">
          <WatchlistPanel
            onSelect={(symbol, name) => {
              setSelected({ symbol, name })
              setActiveTab('chart')
            }}
            selectedSymbol={selected.symbol}
          />
        </div>

        {/* Right: tabs + content */}
        <div className="flex flex-col flex-1 min-w-0">
          {/* Tab bar */}
          <div className="flex items-center gap-1 px-3 py-2 border-b border-[#2A2A2A] bg-[#141414] flex-shrink-0">
            {[
              { id: 'chart', label: '📊 K線圖' },
              { id: 'analysis', label: '🔍 個股分析' },
              { id: 'report', label: '📋 每日報告' },
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

            {/* Interval toggle (only shown in chart tab) */}
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
              {reportMsg && <span className="text-xs text-green-400">{reportMsg}</span>}
              {hasPdf && (
                <a
                  href={api.downloadPdfUrl()}
                  target="_blank"
                  rel="noreferrer"
                  className="px-3 py-1 text-xs bg-[#1A237E] hover:bg-[#283593] text-blue-300 rounded transition-colors"
                >
                  📄 下載PDF
                </a>
              )}
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="px-3 py-1 text-xs bg-[#1B5E20] hover:bg-[#2E7D32] text-green-300 rounded disabled:opacity-50 transition-colors"
              >
                {generating ? '⏳ 生成中...' : '▶ 生成每日報告'}
              </button>
            </div>
          </div>

          {/* Content area */}
          <div className="flex-1 min-h-0 overflow-hidden">
            {activeTab === 'chart' && (
              <StockChart
                symbol={selected.symbol}
                stockName={selected.name}
                interval={interval}
              />
            )}
            {activeTab === 'analysis' && (
              <AnalysisPanel symbol={selected.symbol} stockName={selected.name} mode="single" />
            )}
            {activeTab === 'report' && (
              <AnalysisPanel symbol={selected.symbol} stockName={selected.name} mode="report" />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
