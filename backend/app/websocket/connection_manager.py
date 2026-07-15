"""In-process WebSocket connection manager.

Tracks live client sockets grouped by ``execution_id`` and broadcasts
notification events to them. Notification-only: PostgreSQL remains the source
of truth and this manager never persists anything. Safe for a single API
instance (MVP); a multi-instance deployment would need a pub/sub layer.
"""

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("app.websocket")


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, execution_id: str, websocket: WebSocket) -> None:
        """Register an already-accepted socket under an execution."""
        async with self._lock:
            self._connections.setdefault(execution_id, set()).add(websocket)

    async def disconnect(self, execution_id: str, websocket: WebSocket) -> None:
        """Remove a socket and drop the execution bucket once empty."""
        async with self._lock:
            sockets = self._connections.get(execution_id)
            if sockets is None:
                return
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(execution_id, None)

    async def broadcast(self, execution_id: str, message: dict[str, Any]) -> None:
        """Send ``message`` to every subscriber of ``execution_id``.

        Broken sockets are collected and removed; a failing send never raises to
        the caller, so a broadcast can never fail a workflow state transition.
        """
        async with self._lock:
            sockets = list(self._connections.get(execution_id, ()))

        if not sockets:
            return

        broken: list[WebSocket] = []
        for websocket in sockets:
            try:
                await websocket.send_json(message)
            except Exception:
                logger.warning("dropping broken websocket for execution %s", execution_id)
                broken.append(websocket)

        for websocket in broken:
            await self.disconnect(execution_id, websocket)

    async def connection_count(self, execution_id: str) -> int:
        async with self._lock:
            return len(self._connections.get(execution_id, ()))


# Module-level singleton shared by the API endpoint and broadcaster.
_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    return _manager
