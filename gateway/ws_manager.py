"""
gateway/ws_manager.py
Gestiona las conexiones WebSocket activas por transfer_id.
El orquestador llama a notify() para enviar actualizaciones en tiempo real.
"""
import asyncio
import json
from fastapi import WebSocket
from collections import defaultdict


class ConnectionManager:
    def __init__(self):
        # transfer_id → lista de websockets activos
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, transfer_id: str, ws: WebSocket):
        await ws.accept()
        self._connections[transfer_id].append(ws)

    def disconnect(self, transfer_id: str, ws: WebSocket):
        self._connections[transfer_id].remove(ws)
        if not self._connections[transfer_id]:
            del self._connections[transfer_id]

    async def notify(self, transfer_id: str, event: dict):
        """Envía un evento a todos los WS suscritos a esta transferencia."""
        dead = []
        for ws in self._connections.get(transfer_id, []):
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[transfer_id].remove(ws)

    async def broadcast_final(self, transfer_id: str, status: str, steps: list):
        """Envía el evento final de la saga y cierra las conexiones."""
        await self.notify(transfer_id, {
            "transfer_id": transfer_id,
            "step": "FINAL",
            "status": status,
            "steps": steps,
        })


manager = ConnectionManager()
