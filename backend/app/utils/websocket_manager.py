"""In-memory WebSocket connection manager.

A singleton-ish helper used by the realtime endpoint to fan out trading
signals to every connected client. For multi-worker deployments this should
be replaced with a Redis pub/sub bridge — kept simple for the MVP.
"""

import asyncio
import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a JSON-serialisable payload to every connected client.

        Dead sockets are pruned silently so a single bad client cannot block
        the broadcast for everyone else.
        """
        payload = json.dumps(message, default=str)

        async with self._lock:
            targets = list(self._connections)

        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)


# Process-wide singleton.
manager = ConnectionManager()
