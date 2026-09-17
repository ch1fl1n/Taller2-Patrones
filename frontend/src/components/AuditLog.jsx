import { useState } from 'react'
import { getAudit } from '../services/api'
import StatusBadge from './StatusBadge'

export default function AuditLog({ transferId }) {
  const [rows, setRows]       = useState([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen]       = useState(false)

  const load = async () => {
    if (!transferId) return
    setLoading(true)
    try {
      const data = await getAudit(transferId)
      setRows(data)
      setOpen(true)
    } catch { /* ignorar */ }
    finally { setLoading(false) }
  }

  return (
    <div className="bg-gray-800 rounded-xl p-4 space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider">
          📂 Bitácora de Auditoría
        </h2>
        <button
          onClick={load}
          disabled={!transferId || loading}
          className="text-xs bg-gray-700 hover:bg-gray-600 disabled:bg-gray-700 disabled:opacity-50 px-3 py-1 rounded-lg"
        >
          {loading ? 'Cargando...' : 'Refrescar'}
        </button>
      </div>

      {open && rows.length === 0 && (
        <p className="text-xs text-gray-500">Sin registros todavía.</p>
      )}

      {open && rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500 border-b border-gray-700">
                <th className="text-left py-1 pr-3">Paso</th>
                <th className="text-left py-1 pr-3">Estado</th>
                <th className="text-left py-1 pr-3">Modo</th>
                <th className="text-left py-1">Hora</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="py-1 pr-3 text-gray-300 font-mono">{r.step_name}</td>
                  <td className="py-1 pr-3"><StatusBadge status={r.step_status} /></td>
                  <td className="py-1 pr-3 text-gray-500">{r.saga_mode}</td>
                  <td className="py-1 text-gray-500">
                    {new Date(r.created_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
