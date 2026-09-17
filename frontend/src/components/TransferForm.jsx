import { useState, useEffect } from 'react'
import { getAccounts } from '../services/api'

export default function TransferForm({ onSubmit, loading }) {
  const [accounts, setAccounts]         = useState([])
  const [sourceAccount, setSource]      = useState('')
  const [targetAccount, setTarget]      = useState('')
  const [amount, setAmount]             = useState('')
  const [sagaMode, setSagaMode]         = useState('orchestration')
  const [idempotencyKey, setIdempKey]   = useState('')

  useEffect(() => {
    getAccounts()
      .then(data => {
        setAccounts(data)
        if (data.length >= 2) {
          setSource(data[0].account_code)
          setTarget(data[1].account_code)
        }
      })
      .catch(() => {})
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({ sourceAccount, targetAccount, amount: parseFloat(amount), sagaMode, idempotencyKey })
  }

  const inputCls = 'w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
  const labelCls = 'block text-xs text-gray-400 mb-1'

  return (
    <form onSubmit={handleSubmit} className="bg-gray-800 rounded-xl p-4 space-y-3">
      <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider">
        🏦 Nueva Transferencia
      </h2>

      <div>
        <label className={labelCls}>Cuenta Origen</label>
        <select className={inputCls} value={sourceAccount} onChange={e => setSource(e.target.value)}>
          {accounts.map(a => (
            <option key={a.account_code} value={a.account_code}>
              {a.account_code} — {a.owner_name} (${parseFloat(a.balance).toLocaleString()})
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className={labelCls}>Cuenta Destino</label>
        <select className={inputCls} value={targetAccount} onChange={e => setTarget(e.target.value)}>
          {accounts.filter(a => a.account_code !== sourceAccount).map(a => (
            <option key={a.account_code} value={a.account_code}>
              {a.account_code} — {a.owner_name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className={labelCls}>Importe (USD)</label>
        <input
          type="number" min="1" step="0.01" required
          className={inputCls}
          placeholder="5000.00"
          value={amount}
          onChange={e => setAmount(e.target.value)}
        />
      </div>

      <div>
        <label className={labelCls}>Modo Saga</label>
        <select className={inputCls} value={sagaMode} onChange={e => setSagaMode(e.target.value)}>
          <option value="orchestration">🎯 Orquestación (orquestador central)</option>
          <option value="choreography">🎭 Coreografía (eventos Redis)</option>
        </select>
      </div>

      <div>
        <label className={labelCls}>Clave de Idempotencia (CP-05 — dejar vacío para auto-generar)</label>
        <input
          type="text"
          className={inputCls}
          placeholder="uuid-v4 opcional"
          value={idempotencyKey}
          onChange={e => setIdempKey(e.target.value)}
        />
      </div>

      <button
        type="submit"
        disabled={loading || !amount || !sourceAccount || !targetAccount}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg py-2 text-sm font-semibold transition-colors"
      >
        {loading ? '⏳ Procesando...' : '🚀 Enviar Transferencia'}
      </button>
    </form>
  )
}
