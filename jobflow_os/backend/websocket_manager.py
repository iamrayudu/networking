import asyncio
import json
import logging
from fastapi import WebSocket

_log = logging.getLogger('websocket_manager')


class WebSocketManager:
    def __init__(self):
        self.connections: dict = {}  # { connection_id: ws }
        self.loop = None
        self._counter = 0

    async def connect(self, ws: WebSocket) -> str:
        await ws.accept()
        self._counter += 1
        conn_id = f'client_{self._counter}'
        self.connections[conn_id] = ws
        _log.info(f'WS connected: {conn_id} (total={len(self.connections)})')
        return conn_id

    def disconnect(self, conn_id: str):
        self.connections.pop(conn_id, None)
        _log.info(f'WS disconnected: {conn_id} (remaining={len(self.connections)})')

    async def broadcast(self, event_type: str, payload: dict):
        """Send to all connected clients."""
        msg = json.dumps({'type': event_type, 'payload': payload})
        dead = []
        for conn_id, ws in list(self.connections.items()):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(conn_id)
        for conn_id in dead:
            self.connections.pop(conn_id, None)

    def broadcast_sync(self, event_type: str, payload: dict):
        """Thread-safe broadcast from agent threads."""
        if not self.loop or not self.connections:
            return
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.broadcast(event_type, payload), self.loop
            )
            future.result(timeout=5)
        except Exception as e:
            _log.warning(f'broadcast_sync failed: {e}')


ws_manager = WebSocketManager()
