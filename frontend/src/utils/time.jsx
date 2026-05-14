export function formatUpdateTime(value) {
  if (!value) return ''
  try {
    const date = new Date(value)
    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleString('zh-TW', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      })
    }
  } catch {}
  return String(value).replace('T', ' ').slice(0, 16)
}

export function UpdateTime({ value, label = '後端更新' }) {
  const text = formatUpdateTime(value)
  if (!text) return null
  return <span className="text-[10px] text-gray-600 whitespace-nowrap">{label}：{text}</span>
}
