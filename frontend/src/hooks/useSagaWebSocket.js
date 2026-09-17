import { useEffect, useRef, useCallback } from 'react'

const WS_BASE = 'ws://localhost:8000'

/**
 * Se conecta al WebSocket del gateway para un transfer_id dado.
 * Llama onEvent(event) por cada mensaje recibido.
 * Retorna una función disconnect() para cerrar manualmente.
 */
export function useSagaWebSocket(transferId, onEvent) {
  const wsRef = useRef(null)

  const connect = useCallback((id) => {
    if (!id) return
    const ws = new WebSocket(`${WS_BASE}/ws/${id}`)

    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        onEvent(event)
      } catch { /* ignorar mensajes mal formados */ }
    }

    ws.onerror = () => console.warn('[WS] error de conexión')
    wsRef.current = ws
  }, [onEvent])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
  }, [])

  useEffect(() => {
    connect(transferId)
    return disconnect
  }, [transferId, connect, disconnect])

  return { disconnect }
}
