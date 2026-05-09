import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/stocks.js'

const CATEGORIES = [
  'IC設計', 'IC代工', '封裝測試', '系統模組PCB',
  '記憶體', '功率半導體', '磊晶', 'AI與雲端',
  '資源與原物料', '總體經濟',
]

function parsePubDate(str) {
  if (!str) return ''
  try {
    const d = new Date(str)
    if (isNaN(d.getTime())) return str
    return d.toLocaleDateString('zh-TW', { month: '2-digit', day: '2-digit' })
      + ' ' + d.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false })
  } catch {
    return str
  }
}

function NewsCard({ article }) {
  const isEn = article.lang && article.lang.startsWith('en')
  return (
    <a
      href={article.link}
      target="_blank"
      rel="noreferrer noopener"
      className="block group px-3 py-2.5 border-b border-[#1A1A1A] hover:bg-[#141414] transition-colors"
    >
      <div className="flex items-start gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-[11px] text-gray-200 group-hover:text-white leading-snug line-clamp-2">
            {article.title}
          </p>
          <div className="flex items-center gap-2 mt-1">
            {article.source && (
              <span className="text-[9px] text-gray-500 truncate max-w-[120px]">{article.source}</span>
            )}
            {article.pub_date && (
              <span className="text-[9px] text-gray-600 flex-shrink-0">{parsePubDate(article.pub_date)}</span>
            )}
            <span className={`text-[8px] px-1 rounded flex-shrink-0 ${
              isEn ? 'bg-[#1A2A1A] text-green-600' : 'bg-[#1A1A2A] text-blue-600'
            }`}>
              {isEn ? 'EN' : '中'}
            </span>
          </div>
        </div>
        <span className="text-gray-700 group-hover:text-gray-400 text-[10px] flex-shrink-0 mt-0.5">↗</span>
      </div>
    </a>
  )
}

export default function NewsPanel() {
  const [activeCategory, setActiveCategory] = useState(CATEGORIES[0])
  const [newsData, setNewsData] = useState({})
  const [lastUpdated, setLastUpdated] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadNews = useCallback(async (force = false) => {
    setLoading(true)
    setError('')
    try {
      const res = await api.getNews(null, force)
      setNewsData(res.news || {})
      setLastUpdated(res.last_updated || {})
    } catch (e) {
      setError('新聞載入失敗：' + e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadNews() }, [loadNews])

  const articles = newsData[activeCategory] || []
  const updatedAt = lastUpdated[activeCategory] || ''

  return (
    <div className="flex flex-col h-full bg-[#0A0A0A]">
      {/* Category tabs — horizontal scrollable */}
      <div className="flex-shrink-0 overflow-x-auto border-b border-[#1A1A1A] bg-[#0D0D0D]">
        <div className="flex gap-1 px-2 py-2 min-w-max">
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-2.5 py-1 rounded text-[10px] whitespace-nowrap transition-colors flex-shrink-0 ${
                activeCategory === cat
                  ? 'bg-blue-800 text-white'
                  : 'bg-[#1A1A1A] text-gray-400 hover:text-white hover:bg-[#222]'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Header bar */}
      <div className="flex-shrink-0 flex items-center justify-between px-3 py-1.5 border-b border-[#1A1A1A] bg-[#111]">
        <span className="text-[10px] text-gray-500">
          {updatedAt ? `更新：${updatedAt}` : ''}
        </span>
        <div className="flex items-center gap-2">
          {loading && <span className="text-[9px] text-blue-400">載入中...</span>}
          {error && <span className="text-[9px] text-red-400">{error}</span>}
          <button
            onClick={() => loadNews(true)}
            disabled={loading}
            className="text-[9px] text-gray-500 hover:text-gray-300 disabled:opacity-40 border border-[#2A2A2A] px-2 py-0.5 rounded"
          >
            重新整理
          </button>
        </div>
      </div>

      {/* News list */}
      <div className="flex-1 overflow-y-auto">
        {articles.length === 0 && !loading && (
          <div className="flex items-center justify-center h-32 text-[11px] text-gray-600">
            {error ? error : '暫無新聞資料'}
          </div>
        )}
        {articles.map((art, i) => (
          <NewsCard key={art.link || i} article={art} />
        ))}
      </div>
    </div>
  )
}
