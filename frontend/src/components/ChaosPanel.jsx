/**
 * Panel de interruptores de caos.
 * Permite forzar cada escenario de fallo (CP-02 a CP-05).
 */
export default function ChaosPanel({ chaos, onChange }) {
  const toggle = (key) => onChange({ ...chaos, [key]: !chaos[key] })

  const switches = [
    { key: 'force_insufficient_funds', label: 'CP-02 · Fondos insuficientes', color: 'yellow' },
    { key: 'force_fraud',              label: 'CP-03 · Forzar fraude',         color: 'orange' },
    { key: 'force_network_timeout',    label: 'CP-04 · Timeout red externa',   color: 'red'    },
  ]

  return (
    <div className="bg-gray-800 rounded-xl p-4 space-y-3">
      <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider">
        ⚡ Panel de Caos
      </h2>
      {switches.map(({ key, label, color }) => (
        <label key={key} className="flex items-center justify-between cursor-pointer">
          <span className={`text-sm text-${color}-300`}>{label}</span>
          <div
            onClick={() => toggle(key)}
            className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${
              chaos[key] ? `bg-${color}-500` : 'bg-gray-600'
            }`}
          >
            <span
              className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform duration-200 ${
                chaos[key] ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </div>
        </label>
      ))}
    </div>
  )
}
