"""
gateway/routers/websocket.py

WS /ws/{transfer_id}
El frontend se conecta aquí y recibe eventos en tiempo real de la Saga.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from gateway.ws_manager import manager

router = APIRouter()


@router.websocket("/ws/{transfer_id}")
async def websocket_endpoint(transfer_id: str, ws: WebSocket):
    await manager.connect(transfer_id, ws)
    try:
        while True:
            # Mantener la conexión viva; el servidor empuja los mensajes
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(transfer_id, ws)
