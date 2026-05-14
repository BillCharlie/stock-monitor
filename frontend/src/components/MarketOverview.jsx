import { useEffect, useState } from 'react'
import { api } from '../api/stocks.js'
import { UpdateTime } from '../utils/time.jsx'

function IndexCard({ item }) {
  const isUp = item.change_pct >= 0
  const color = isUp ? 'text-[#EF5350]' : 'text-[#26A69A]'
  const arrow = isUp ? '▲' : '▼'
  return (
    <div className="flex flex-col px-3 py-1.5 border-r border-[#2A2A2A] last:border-r-0 min-w-0">
      <span className="text-[10px] text-gray-500 truncate">{item.name}</span>
      <div className="flex items-baseline gap-1.5">
        <span className="text-white font-mono text-xs">
          {item.price != null ? item.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}
        </span>
        {item.change_pct != null && (
          <span className={`text-[10px] font-mono ${color}`}>
            {arrow} {Math.abs(item.change_pct).toFixed(2)}%
          </span>
        )}
      </div>
    </div>
  )
}

export default function MarketOverview() {
  const [indices, setIndices] = useState([])
  const [lastUpdate, setLastUpdate] = useState('')

  const load = async () => {
    try {
      const data = await api.getMarketOverview()
      setIndices(data.indices || [])
      setLastUpdate(data.last_updated || '')
    } catch {
      // silently ignore
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 5 * 60 * 1000) // refresh every 5 min
    return () => clearInterval(id)
  }, [])

  return (
    <div className="flex items-center bg-[#0A0A0A] border-b border-[#2A2A2A] h-10 overflow-x-auto flex-shrink-0">
      <div className="flex items-center px-3 border-r border-[#2A2A2A] flex-shrink-0">
        <span className="text-xs font-bold text-blue-400">股市監控</span>
        <span className="text-[10px] text-gray-600 ml-2">📈</span>
      </div>
      <div className="flex flex-1 overflow-x-auto">
        {indices.map(idx => <IndexCard key={idx.symbol} item={idx} />)}
      </div>
      {lastUpdate && (
        <div className="px-3 flex-shrink-0">
          <UpdateTime value={lastUpdate} label="後端更新" />
        </div>
      )}
    </div>
  )
}
