import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api/stocks.js'

const SECTION_TABS = [
  { id: 'english_news', label: '英文新聞' },
  { id: 'x_posts', label: 'X' },
  { id: 'truth_posts', label: 'Truth' },
  { id: 'white_house', label: '白宮' },
]

function formatDate(value) {
  if (!value) return ''
  try {
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return value
    return d.toLocaleDateString('zh-TW', { month: '2-digit', day: '2-digit' })
      + ' ' + d.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false })
  } catch {
    return value
  }
}

function isHistorical(value) {
  if (!value) return false
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return false
  return Date.now() - d.getTime() > 21 * 24 * 60 * 60 * 1000
}

function normalizeText(value) {
  return String(value || '').toLowerCase()
}

function itemMatchesPolicyTheme(item, theme) {
  if (!item || !theme) return false
  const ids = [
    ...(item.market_tag_ids || []),
    ...(item.policy_theme_ids || []),
  ].map(String)
  if (theme.id && ids.includes(String(theme.id))) return true

  const labels = [
    ...(item.market_tags || []),
    ...(item.policy_theme_labels || []),
  ].map(String)
  if (theme.label && labels.includes(String(theme.label))) return true

  const haystack = normalizeText([
    item.title,
    item.summary,
    item.source,
    labels.join(' '),
  ].filter(Boolean).join(' '))
  return (theme.keywords || []).some(keyword => haystack.includes(normalizeText(keyword)))
}

function getSectionItems(sections) {
  const seen = new Set()
  const items = []
  for (const tab of SECTION_TABS) {
    for (const item of sections[tab.id] || []) {
      const key = item.id || item.link || `${item.title || ''}|${item.published_at || item.pub_date || ''}`
      if (seen.has(key)) continue
      seen.add(key)
      items.push({
        ...item,
        _sectionId: tab.id,
        _sectionLabel: tab.label,
      })
    }
  }
  return items
}

function getItemTime(item) {
  const value = item?.published_at || item?.pub_date
  if (!value) return 0
  const time = new Date(value).getTime()
  return Number.isNaN(time) ? 0 : time
}

function sortNewestFirst(items) {
  return [...items].sort((a, b) => getItemTime(b) - getItemTime(a))
}

function ImpactSummary({ impact, selectedThemeId, onSelectTheme, filteredCount, onClearTheme }) {
  const themes = impact?.themes || []
  const sectors = impact?.sectors || []
  const selectedTheme = themes.find(theme => String(theme.id) === String(selectedThemeId))
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border-b border-[#1A1A1A] bg-[#101214] px-3 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-semibold text-[#40C4FF]">政策訊號</span>
        <span className="text-[10px] text-gray-300">{impact?.overall || '目前未偵測到明確市場板塊衝擊訊號'}</span>
        {selectedTheme && (
          <span className="text-[9px] text-[#40C4FF] border border-[#1E4E66] bg-[#071722] rounded px-1.5 py-0.5">
            已篩選 {filteredCount} 則
          </span>
        )}
        {selectedTheme && (
          <button
            type="button"
            onClick={onClearTheme}
            className="text-[9px] text-gray-500 hover:text-white border border-[#2A2A2A] rounded px-1.5 py-0.5"
          >
            清除
          </button>
        )}
        <button
          type="button"
          onClick={() => setExpanded(value => !value)}
          className="ml-auto text-[9px] text-gray-500 hover:text-white border border-[#2A2A2A] rounded px-1.5 py-0.5"
        >
          {expanded ? '收合訊號' : '展開訊號'}
        </button>
      </div>

      {expanded && themes.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-1.5 mt-2">
          {themes.slice(0, 6).map(theme => {
            const selected = String(theme.id) === String(selectedThemeId)
            return (
              <button
                key={theme.id}
                type="button"
                aria-pressed={selected}
                onClick={() => onSelectTheme?.(theme)}
                className={`text-left border rounded px-2 py-1.5 min-h-[52px] transition-colors ${
                  selected
                    ? 'border-[#40C4FF] bg-[#0A2433] shadow-[0_0_0_1px_rgba(64,196,255,0.18)]'
                    : 'border-[#202833] bg-[#0C1117] hover:border-[#31465B] hover:bg-[#101923]'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] text-white truncate">{theme.label}</span>
                  <span className="text-[9px] text-[#FFA726] flex-shrink-0">{theme.bias}</span>
                </div>
                <div className="flex items-center gap-1 mt-1 text-[9px] leading-snug">
                  <span className="text-gray-500 truncate">{(theme.sectors || []).slice(0, 4).join('、')}</span>
                  <span className="text-gray-600 flex-shrink-0">{theme.hit_count || 0} 則</span>
                </div>
              </button>
            )
          })}
        </div>
      )}

      {expanded && sectors.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {sectors.slice(0, 8).map(sector => (
            <span key={sector.sector} className="text-[9px] px-1.5 py-0.5 rounded bg-[#172018] text-[#8BC34A] border border-[#263A25]">
              {sector.sector}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function SourceItem({ item, showSection = false }) {
  const text = item.summary || item.title
  const tags = item.market_tags || []
  const historical = isHistorical(item.published_at || item.pub_date)

  return (
    <a
      href={item.link || '#'}
      target="_blank"
      rel="noreferrer noopener"
      className="group block px-3 py-2.5 border-b border-[#161616] hover:bg-[#141414] transition-colors"
    >
      <div className="flex items-start gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {showSection && item._sectionLabel && (
              <span className="text-[8px] text-[#8BC34A] border border-[#263A25] rounded px-1">{item._sectionLabel}</span>
            )}
            <span className="text-[9px] text-[#40C4FF]">{item.source}</span>
            {item.aggregator && (
              <span className="text-[8px] text-gray-600 border border-[#2A2A2A] rounded px-1">{item.aggregator}</span>
            )}
            {historical && (
              <span className="text-[8px] text-yellow-600 border border-yellow-900/60 rounded px-1">歷史</span>
            )}
            <span className="text-[9px] text-gray-600 ml-auto flex-shrink-0">{formatDate(item.published_at || item.pub_date)}</span>
          </div>
          <p className="text-[11px] text-gray-100 leading-snug break-words">
            {item.title}
          </p>
          {text && text !== item.title && (
            <p className="text-[10px] text-gray-500 leading-snug mt-1 break-words">
              {text}
            </p>
          )}
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {tags.slice(0, 4).map(tag => (
                <span key={tag} className="text-[8px] px-1 rounded bg-[#1A1A0A] text-[#FFA726]">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
        <span className="text-gray-700 group-hover:text-gray-400 text-[10px] flex-shrink-0 mt-0.5">↗</span>
      </div>
    </a>
  )
}

export default function TrumpNewsPanel() {
  const [activeSection, setActiveSection] = useState('truth_posts')
  const [selectedThemeId, setSelectedThemeId] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadTrumpNews = useCallback(async (force = false) => {
    setLoading(true)
    setError('')
    try {
      const res = await api.getTrumpNews(force)
      setData(res)
    } catch (e) {
      setError('TrumpNews 載入失敗：' + e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTrumpNews()
    const id = window.setInterval(() => loadTrumpNews(false), 5 * 60 * 60 * 1000)
    return () => window.clearInterval(id)
  }, [loadTrumpNews])

  const sections = data?.sections || {}
  const activeItems = sections[activeSection] || []
  const allItems = useMemo(() => getSectionItems(sections), [sections])
  const themes = data?.impact?.themes || []
  const selectedTheme = themes.find(theme => String(theme.id) === String(selectedThemeId))
  const filteredItems = useMemo(() => {
    if (!selectedTheme) return []
    return allItems.filter(item => itemMatchesPolicyTheme(item, selectedTheme))
  }, [allItems, selectedTheme])
  const visibleItems = useMemo(
    () => sortNewestFirst(selectedTheme ? filteredItems : activeItems),
    [activeItems, filteredItems, selectedTheme],
  )
  const counts = useMemo(() => {
    const out = {}
    for (const tab of SECTION_TABS) out[tab.id] = (sections[tab.id] || []).length
    return out
  }, [sections])

  return (
    <div className="flex flex-col h-full bg-[#0A0A0A]">
      <div className="flex-shrink-0 flex items-center gap-2 px-3 py-2 border-b border-[#1A1A1A] bg-[#0D0D0D]">
        <span className="text-[11px] font-semibold text-white">TrumpNews</span>
        <span className="text-[9px] text-gray-600">每 5 小時自動抓取</span>
        <div className="ml-auto flex items-center gap-2 pl-2">
          {data?.last_updated && (
            <span className="text-[9px] text-gray-600 whitespace-nowrap">更新：{data.last_updated}</span>
          )}
          {loading && <span className="text-[9px] text-blue-400 whitespace-nowrap">載入中...</span>}
          {error && <span className="text-[9px] text-red-400 whitespace-nowrap">{error}</span>}
          <button
            onClick={() => loadTrumpNews(true)}
            disabled={loading}
            className="text-[9px] text-gray-500 hover:text-gray-300 disabled:opacity-40 border border-[#2A2A2A] px-2 py-0.5 rounded whitespace-nowrap"
          >
            重新整理
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        <ImpactSummary
          impact={data?.impact}
          selectedThemeId={selectedThemeId}
          filteredCount={filteredItems.length}
          onClearTheme={() => setSelectedThemeId('')}
          onSelectTheme={(theme) => {
            setSelectedThemeId(prev => (String(prev) === String(theme.id) ? '' : theme.id))
          }}
        />

        <div className="sticky top-0 z-20 flex items-center gap-1 px-2 py-2 border-b border-[#1A1A1A] bg-[#0D0D0D] overflow-x-auto">
          {SECTION_TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveSection(tab.id)
                setSelectedThemeId('')
              }}
              className={`px-2.5 py-1 rounded text-[10px] whitespace-nowrap transition-colors flex-shrink-0 ${
                activeSection === tab.id
                  ? 'bg-[#0D47A1] text-white'
                  : 'bg-[#1A1A1A] text-gray-400 hover:text-white hover:bg-[#222]'
              }`}
            >
              {tab.label}
              <span className="ml-1 text-[9px] opacity-60">{counts[tab.id] || 0}</span>
            </button>
          ))}
        </div>

        {selectedTheme && (
          <div className="flex items-center gap-2 border-b border-[#1A1A1A] bg-[#0B0F12] px-3 py-1.5">
            <span className="text-[10px] text-[#40C4FF] truncate">訊號篩選：{selectedTheme.label}</span>
            <span className="text-[9px] text-gray-500 flex-shrink-0">全部來源 {filteredItems.length} 則</span>
          </div>
        )}
        {visibleItems.length === 0 && !loading && (
          <div className="flex items-center justify-center h-32 text-[11px] text-gray-600">
            {error || (selectedTheme ? '沒有找到此政策訊號的相關內容' : '暫無 TrumpNews 資料')}
          </div>
        )}
        {visibleItems.map((item, i) => (
          <SourceItem
            key={item.id || item.link || `${item._sectionId || activeSection}-${i}`}
            item={item}
            showSection={Boolean(selectedTheme)}
          />
        ))}
      </div>
    </div>
  )
}
