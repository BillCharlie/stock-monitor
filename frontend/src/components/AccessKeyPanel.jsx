import { useState } from 'react'
import { keys, api } from '../api/stocks.js'

function KeyRow({ label, hint, value, onChange, onSave, onClear, status, msg }) {
  const loading = status === 'loading'
  return (
    <div className="mb-5">
      <label className="block text-gray-400 text-xs mb-1">{label}</label>
      <input
        type="password"
        value={value}
        onChange={e => onChange(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && onSave()}
        placeholder={`輸入${label}...`}
        className="w-full bg-[#0D0D0D] border border-[#333] rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
      />
      <p className="text-gray-600 text-xs mt-1">{hint}</p>
      {msg && (
        <p className={`text-xs mt-1 ${status === 'ok' ? 'text-green-400' : status === 'error' ? 'text-yellow-400' : 'text-gray-400'}`}>
          {msg}
        </p>
      )}
      <div className="flex gap-2 mt-2">
        <button
          onClick={onSave}
          disabled={loading}
          className="flex-1 py-1.5 rounded text-xs bg-blue-700 hover:bg-blue-600 text-white transition-colors disabled:opacity-50"
        >
          {loading ? '驗證中...' : '登入並儲存'}
        </button>
        <button
          onClick={onClear}
          disabled={loading}
          className="px-3 py-1.5 rounded text-xs border border-[#333] text-gray-400 hover:text-white hover:border-gray-500 transition-colors disabled:opacity-40"
        >
          清除
        </button>
      </div>
    </div>
  )
}

export default function AccessKeyPanel({ onClose }) {
  const [reportKey, setReportKey] = useState(keys.getReport())
  const [stockKey,  setStockKey]  = useState(keys.getStock())
  const [reportStatus, setReportStatus] = useState('')
  const [reportMsg,    setReportMsg]    = useState('')
  const [stockStatus,  setStockStatus]  = useState('')
  const [stockMsg,     setStockMsg]     = useState('')

  const handleSave = async (type) => {
    const isReport = type === 'report'
    const val = (isReport ? reportKey : stockKey).trim()
    const setStatus = isReport ? setReportStatus : setStockStatus
    const setMsg    = isReport ? setReportMsg    : setStockMsg

    if (isReport) keys.setReport(val)
    else          keys.setStock(val)

    if (!val) { setStatus(''); setMsg(''); return }

    setStatus('loading')
    setMsg('驗證中...')
    try {
      const res = await api.pingAuth(type).catch(() => ({ verified: false }))
      if (res.verified) {
        setStatus('ok')
        setMsg('✓ 驗證成功，已通知管理員')
        setTimeout(() => { setStatus(''); setMsg('') }, 3000)
      } else {
        setStatus('error')
        setMsg('⚠ 密鑰無效或後端未設定')
        setTimeout(() => { setStatus(''); setMsg('') }, 3000)
      }
    } catch {
      setStatus('error')
      setMsg('無法連接後端')
      setTimeout(() => { setStatus(''); setMsg('') }, 3000)
    }
  }

  const handleClear = (type) => {
    if (type === 'report') {
      setReportKey(''); keys.setReport('')
      setReportStatus(''); setReportMsg('')
    } else {
      setStockKey(''); keys.setStock('')
      setStockStatus(''); setStockMsg('')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-[#1A1A1A] border border-[#333] rounded-lg p-6 w-80 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-white font-semibold text-base">存取密鑰設定</h2>
          <button onClick={onClose} className="text-gray-600 hover:text-gray-300 text-lg leading-none">×</button>
        </div>
        <p className="text-gray-500 text-xs mb-5">密鑰儲存於瀏覽器本地，不會上傳。登入成功將通知管理員。</p>

        <KeyRow
          label="報告生成密鑰"
          hint="用於「生成每日報告」與「新聞重新整理」"
          value={reportKey}
          onChange={setReportKey}
          onSave={() => handleSave('report')}
          onClear={() => handleClear('report')}
          status={reportStatus}
          msg={reportMsg}
        />

        <KeyRow
          label="股票管理密鑰"
          hint="用於「新增/刪除自選股票」"
          value={stockKey}
          onChange={setStockKey}
          onSave={() => handleSave('stock')}
          onClear={() => handleClear('stock')}
          status={stockStatus}
          msg={stockMsg}
        />
      </div>
    </div>
  )
}
