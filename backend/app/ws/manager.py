"""Connection manager that fans out events to all connected WebSocket clients.

v1 is a single local user, so we broadcast every event to every socket rather than
maintaining per-agent subscriptions. The manager is a process-wide singleton
(``get_manager``) so services can broadcast without a request context.
"""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

from fastapi import WebSocket

from app.schemas.ws import WSEvent

logger = logging.getLogger(__name__)


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

    async def send_personal(self, websocket: WebSocket, event: WSEvent) -> None:
        """Send an event to a single client (e.g. the connect snapshot or an error reply).

        A dead socket is dropped rather than raised, mirroring ``broadcast``.
        """
        try:
            await websocket.send_json(event.model_dump(mode="json"))
        except Exception:  # noqa: BLE001 - a dead socket shouldn't break the caller
            logger.debug("Dropping dead websocket connection")
            await self.disconnect(websocket)

    async def broadcast(self, event: WSEvent) -> None:
        """Send an event to every connected client, dropping any that fail."""
        payload = event.model_dump(mode="json")
        async with self._lock:
            targets = list(self._connections)
        stale: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_json(payload)
            except Exception:  # noqa: BLE001 - a dead socket shouldn't break the run
                logger.debug("Dropping dead websocket connection")
                stale.append(websocket)
        if stale:
            async with self._lock:
                for websocket in stale:
                    self._connections.discard(websocket)


@lru_cache
def get_manager() -> ConnectionManager:
    """Return the process-wide ConnectionManager singleton."""
    return ConnectionManager()
