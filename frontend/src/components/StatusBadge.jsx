const COLORS = {
  CONFIRMADO:        'bg-green-500 text-white',
  RECHAZADO_FONDOS:  'bg-yellow-500 text-black',
  RECHAZADO_RIESGO:  'bg-orange-500 text-white',
  RECHAZADO_RED:     'bg-red-500 text-white',
  IN_PROGRESS:       'bg-blue-500 text-white',
  COMPENSADO:        'bg-purple-500 text-white',
  COMPENSATING:      'bg-purple-400 text-white',
  SUCCESS:           'bg-green-600 text-white',
  FAILED:            'bg-red-600 text-white',
  STARTED:           'bg-blue-400 text-white',
  UNKNOWN:           'bg-gray-500 text-white',
}

export default function StatusBadge({ status }) {
  const cls = COLORS[status] ?? COLORS.UNKNOWN
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${cls}`}>
      {status}
    </span>
  )
}
