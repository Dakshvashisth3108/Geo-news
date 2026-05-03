"""Real-time signal stream over WebSocket.

Clients connect to /api/v1/ws/signals and receive a JSON message every time a
new TradingSignal is created. Inbound messages are accepted and ignored; the
channel is intentionally one-way for the MVP (server -> client).
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.utils.websocket_manager import manager

router = APIRouter()


@router.websocket("/ws/signals")
async def signals_stream(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        # Send a hello so clients know the channel is open.
        await websocket.send_json({"event": "connected", "data": {"stream": "signals"}})

        # Keep the connection alive; we don't do anything with inbound frames yet.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        # Defensive: ensure the socket is removed from the pool on any error.
        await manager.disconnect(websocket)
        raise
