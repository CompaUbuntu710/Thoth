import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect

class WSManager:
    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)

    async def broadcast(self, event: str, data: dict):
        payload = json.dumps({"event": event, "data": data})
        async with self._lock:
            conns = list(self._connections)
        stale = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        if stale:
            async with self._lock:
                for ws in stale:
                    if ws in self._connections:
                        self._connections.remove(ws)

    @property
    def count(self):
        return len(self._connections)

ws_manager = WSManager()
