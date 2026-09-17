import StatusBadge from './StatusBadge'

const STEP_LABELS = {
  DEBIT:               '1. Débito contable',
  RISK_VALIDATION:     '2. Validación de riesgo',
  CLEARING_SETTLE:     '3. Liquidación externa',
  CREDIT:              '4. Crédito en destino',
  COMPENSATE_DEBIT:    '↩ Reversa débito',
  COMPENSATE_RISK:     '↩ Reversa riesgo',
  COMPENSATE_CLEARING: '↩ Reversa liquidación',
  FINAL:               'Resultado final',
}

const STEP_ICON = {
  STARTED:     '⏳',
  SUCCESS:     '✅',
  FAILED:      '❌',
  COMPENSATED: '↩️',
  COMPENSATING:'🔄',
  IN_PROGRESS: '⏳',
  CONFIRMADO:  '🏦',
  RECHAZADO_FONDOS:  '💸',
  RECHAZADO_RIESGO:  '🚨',
  RECHAZADO_RED:     '🌐',
}

export default function SagaTimeline({ steps, finalStatus }) {
  if (!steps.length && !finalStatus) return null

  return (
    <div className="bg-gray-800 rounded-xl p-4 space-y-2">
      <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">
        📋 Timeline de la Saga
      </h2>

      <ol className="relative border-l border-gray-600 ml-2 space-y-4">
        {steps.map((s, i) => (
          <li key={i} className="ml-4">
            <span className="absolute -left-1.5 flex items-center justify-center w-3 h-3 rounded-full bg-gray-600 ring-2 ring-gray-800 text-xs">
              {STEP_ICON[s.status] ?? '•'}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-300 font-medium">
                {STEP_LABELS[s.step] ?? s.step}
              </span>
              <StatusBadge status={s.status} />
            </div>
            {s.ledger_entry_id && (
              <p className="text-xs text-gray-500 mt-0.5">entry: {s.ledger_entry_id}</p>
            )}
            {s.external_ref && (
              <p className="text-xs text-gray-500 mt-0.5">ref: {s.external_ref}</p>
            )}
            {s.risk_score !== undefined && (
              <p className="text-xs text-gray-500 mt-0.5">risk score: {s.risk_score}</p>
            )}
            {s.reason && (
              <p className="text-xs text-red-400 mt-0.5">{typeof s.reason === 'object' ? JSON.stringify(s.reason) : s.reason}</p>
            )}
          </li>
        ))}
      </ol>

      {finalStatus && (
        <div className="mt-4 pt-3 border-t border-gray-700 flex items-center gap-2">
          <span className="text-sm font-bold text-gray-300">Estado final:</span>
          <StatusBadge status={finalStatus} />
        </div>
      )}
    </div>
  )
}
