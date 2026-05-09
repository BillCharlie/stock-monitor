import { useState } from 'react'
import { keys, api } from '../api/stocks.js'

export default function AccessKeyPanel({ onClose }) {
  const [reportKey, setReportKey] = useState(keys.getReport())
  const [stockKey,  setStockKey]  = useState(keys.getStock())
  const [status, setStatus] = useState('')   // '', 'loading', 'ok', 'error'
  const [msg, setMsg]       = useState('')

  const handleSave = async () => {
    const rk = reportKey.trim()
    const sk = stockKey.trim()

    if (!rk && !sk) {
      keys.setReport(''); keys.setStock('')
      onClose()
      return
    }

    // Store locally first so API headers pick them up
    keys.setReport(rk)
    keys.setStock(sk)

    setStatus('loading')
    setMsg('驗證中...')

    try {
      const calls = []
      if (rk) calls.push(api.pingAuth('report').catch(() => ({ verified: false })))
      if (sk) calls.push(api.pingAuth('stock').catch(() => ({ verified: false })))

      const results = await Promise.all(calls)
      const anyVerified = results.some(r => r.verified)

      if (anyVerified) {
        setStatus('ok')
        setMsg('✓ 密鑰驗證成功，已通知管理員')
      } else {
        setStatus('error')
        setMsg('⚠ 密鑰無效或後端未設定驗證')
      }
      setTimeout(onClose, 1400)
    } catch {
      setStatus('error')
      setMsg('無法連接後端')
      setTimeout(onClose, 1400)
    }
  }

  const handleClear = () => {
    setReportKey(''); setStockKey('')
    keys.setReport(''); keys.setStock('')
    setStatus(''); setMsg('')
  }

  const loading = status === 'loading'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-[#1A1A1A] border border-[#333] rounded-lg p-6 w-80 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <h2 className="text-white font-semibold text-base mb-1">存取密鑰設定</h2>
        <p className="text-gray-500 text-xs mb-4">密鑰儲存於瀏覽器本地，不會上傳。登入成功將通知管理員。</p>

        <div className="mb-4">
          <label className="block text-gray-400 text-xs mb-1">報告生成密鑰</label>
          <input
            type="password"
            value={reportKey}
            onChange={e => setReportKey(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSave()}
            placeholder="輸入報告密鑰..."
            className="w-full bg-[#0D0D0D] border border-[#333] rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
          />
          <p className="text-gray-600 text-xs mt-1">用於「生成每日報告」與「新聞重新整理」</p>
        </div>

        <div className="mb-5">
          <label className="block text-gray-400 text-xs mb-1">股票管理密鑰</label>
          <input
            type="password"
            value={stockKey}
            onChange={e => setStockKey(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSave()}
            placeholder="輸入股票管理密鑰..."
            className="w-full bg-[#0D0D0D] border border-[#333] rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
          />
          <p className="text-gray-600 text-xs mt-1">用於「新增/刪除自選股票」</p>
        </div>

        {msg && (
          <p className={`text-xs mb-3 ${status === 'ok' ? 'text-green-400' : status === 'error' ? 'text-yellow-400' : 'text-gray-400'}`}>
            {msg}
          </p>
        )}

        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={loading}
            className="flex-1 py-2 rounded text-sm bg-blue-700 hover:bg-blue-600 text-white transition-colors disabled:opacity-50"
          >
            {loading ? '驗證中...' : '登入並儲存'}
          </button>
          <button
            onClick={handleClear}
            disabled={loading}
            className="px-3 py-2 rounded text-sm border border-[#333] text-gray-400 hover:text-white hover:border-gray-500 transition-colors disabled:opacity-40"
          >
            清除
          </button>
          <button
            onClick={onClose}
            disabled={loading}
            className="px-3 py-2 rounded text-sm border border-[#333] text-gray-400 hover:text-white hover:border-gray-500 transition-colors disabled:opacity-40"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  )
}
