const BASE = 'http://localhost:8000'

export async function getAccounts() {
  const res = await fetch(`${BASE}/accounts`)
  if (!res.ok) throw new Error('No se pudieron cargar las cuentas')
  return res.json()
}

export async function postTransfer(payload) {
  const res = await fetch(`${BASE}/transfers`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(payload),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Error al iniciar la transferencia')
  return data
}

export async function getAudit(transferId) {
  const res = await fetch(`${BASE}/transfers/${transferId}/audit`)
  if (!res.ok) throw new Error('Error al obtener la auditoría')
  return res.json()
}
