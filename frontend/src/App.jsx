import { useState, useCallback } from 'react'
import TransferForm from './components/TransferForm'
import ChaosPanel   from './components/ChaosPanel'
import SagaTimeline from './components/SagaTimeline'
import AuditLog     from './components/AuditLog'
import StatusBadge  from './components/StatusBadge'
import { postTransfer } from './services/api'
import { useSagaWebSocket } from './hooks/useSagaWebSocket'

const DEFAULT_CHAOS = {
  force_insufficient_funds: false,
  force_fraud:              false,
  force_network_timeout:    false,
}

export default function App() {
  const [chaos, setChaos]               = useState(DEFAULT_CHAOS)
  const [loading, setLoading]           = useState(false)
  const [transferId, setTransferId]     = useState(null)
  const [steps, setSteps]               = useState([])
  const [finalStatus, setFinalStatus]   = useState(null)
  const [error, setError]               = useState(null)
  const [lastKey, setLastKey]           = useState(null)

  // Recibe cada evento del WebSocket y actualiza la timeline
  const onEvent = useCallback((event) => {
    if (event.step === 'FINAL') {
      setFinalStatus(event.status)
      setLoading(false)
    } else {
      setSteps(prev => {
        // Actualizar si el paso ya existe, sino agregar
        const idx = prev.findIndex(s => s.step === event.step)
        if (idx >= 0) {
          const updated = [...prev]
          updated[idx] = event
          return updated
        }
        return [...prev, event]
      })
    }
  }, [])

  useSagaWebSocket(transferId, onEvent)

  const handleSubmit = async ({ sourceAccount, targetAccount, amount, sagaMode, idempotencyKey }) => {
    setLoading(true)
    setSteps([])
    setFinalStatus(null)
    setError(null)
    setTransferId(null)

    try {
      const payload = {
        source_account:  sourceAccount,
        target_account:  targetAccount,
        amount,
        saga_mode:       sagaMode,
        idempotency_key: idempotencyKey || undefined,
        chaos: {
          force_insufficient_funds: chaos.force_insufficient_funds,
          force_fraud:              chaos.force_fraud,
          force_network_timeout:    chaos.force_network_timeout,
        },
      }

      const data = await postTransfer(payload)
      setLastKey(data.idempotency_key)

      // CP-02 o CP-05 resueltos sincrónicamente en el gateway
      if (data.status !== 'IN_PROGRESS') {
        setFinalStatus(data.status)
        setLoading(false)
        if (data.cached) {
          setError('⚡ Petición duplicada detectada (CP-05): respuesta cacheada, sin doble cobro.')
        }
        return
      }

      // Para los demás casos el WS actualiza el estado en tiempo real
      setTransferId(data.transfer_id)

    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-blue-400">🏦 NovaBank International</h1>
            <p className="text-xs text-gray-500">Sistema de Transferencias — Patrón Saga Distribuido</p>
          </div>
          <div className="text-xs text-gray-600 text-right">
            <p>Orquestación · Coreografía</p>
            <p>Consistencia Eventual · BASE</p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 grid grid-cols-1 md:grid-cols-2 gap-6">

        {/* Columna izquierda: formulario + caos */}
        <div className="space-y-4">
          <TransferForm onSubmit={handleSubmit} loading={loading} />
          <ChaosPanel chaos={chaos} onChange={setChaos} />

          {/* Leyenda de casos de prueba */}
          <div className="bg-gray-800 rounded-xl p-4 text-xs text-gray-500 space-y-1">
            <p className="font-semibold text-gray-400 mb-2">Casos de Prueba</p>
            <p>✅ <b>CP-01</b> Sin switches → Camino feliz</p>
            <p>💸 <b>CP-02</b> Switch "Fondos insuficientes"</p>
            <p>🚨 <b>CP-03</b> Switch "Forzar fraude"</p>
            <p>🌐 <b>CP-04</b> Switch "Timeout red externa"</p>
            <p>⚡ <b>CP-05</b> Reenviar la misma clave de idempotencia</p>
          </div>
        </div>

        {/* Columna derecha: timeline + auditoría */}
        <div className="space-y-4">

          {/* Estado actual */}
          {(loading || finalStatus) && (
            <div className="bg-gray-800 rounded-xl p-4 flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-400">Transfer ID</p>
                <p className="font-mono text-xs text-gray-300 truncate max-w-xs">{transferId ?? '—'}</p>
              </div>
              {finalStatus
                ? <StatusBadge status={finalStatus} />
                : <span className="text-blue-400 text-sm animate-pulse">procesando…</span>
              }
            </div>
          )}

          {error && (
            <div className="bg-yellow-900 border border-yellow-700 rounded-xl p-3 text-sm text-yellow-300">
              {error}
            </div>
          )}

          {lastKey && (
            <div className="bg-gray-800 rounded-xl px-4 py-2 text-xs text-gray-500">
              Clave de idempotencia: <span className="font-mono text-gray-400">{lastKey}</span>
              <span className="ml-2 text-gray-600">(cópiala para probar CP-05)</span>
            </div>
          )}

          <SagaTimeline steps={steps} finalStatus={finalStatus} />
          <AuditLog transferId={transferId} />
        </div>
      </main>
    </div>
  )
}
