import { useState } from 'react'
import { keys } from '../api/stocks.js'

export default function AccessKeyPanel({ onClose }) {
  const [reportKey, setReportKey] = useState(keys.getReport())
  const [stockKey,  setStockKey]  = useState(keys.getStock())
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    keys.setReport(reportKey.trim())
    keys.setStock(stockKey.trim())
    setSaved(true)
    setTimeout(() => { setSaved(false); onClose() }, 800)
  }

  const handleClear = () => {
    setReportKey(''); setStockKey('')
    keys.setReport(''); keys.setStock('')
    setSaved(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-[#1A1A1A] border border-[#333] rounded-lg p-6 w-80 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <h2 className="text-white font-semibold text-base mb-1">存取密鑰設定</h2>
        <p className="text-gray-500 text-xs mb-4">密鑰儲存於瀏覽器本地，不會上傳。</p>

        <div className="mb-4">
          <label className="block text-gray-400 text-xs mb-1">報告生成密鑰</label>
          <input
            type="password"
            value={reportKey}
            onChange={e => setReportKey(e.target.value)}
            placeholder="輸入報告密鑰..."
            className="w-full bg-[#0D0D0D] border border-[#333] rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
          />
          <p className="text-gray-600 text-xs mt-1">用於「生成每日報告」按鈕</p>
        </div>

        <div className="mb-5">
          <label className="block text-gray-400 text-xs mb-1">股票管理密鑰</label>
          <input
            type="password"
            value={stockKey}
            onChange={e => setStockKey(e.target.value)}
            placeholder="輸入股票管理密鑰..."
            className="w-full bg-[#0D0D0D] border border-[#333] rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
          />
          <p className="text-gray-600 text-xs mt-1">用於「新增/刪除自選股票」</p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleSave}
            className="flex-1 py-2 rounded text-sm bg-blue-700 hover:bg-blue-600 text-white transition-colors"
          >
            {saved ? '已儲存 ✓' : '儲存'}
          </button>
          <button
            onClick={handleClear}
            className="px-3 py-2 rounded text-sm border border-[#333] text-gray-400 hover:text-white hover:border-gray-500 transition-colors"
          >
            清除
          </button>
          <button
            onClick={onClose}
            className="px-3 py-2 rounded text-sm border border-[#333] text-gray-400 hover:text-white hover:border-gray-500 transition-colors"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  )
}
