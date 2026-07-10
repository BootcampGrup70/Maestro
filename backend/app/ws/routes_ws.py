"""The ``/ws`` WebSocket endpoint.

v1 is push-only: the server streams run events to the client. Inbound messages are
drained (and ignored) to keep the socket alive. Interjecting a new instruction into a
running agent will be handled here later (see TODO).
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.manager import get_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    manager = get_manager()
    await manager.connect(websocket)
    try:
        while True:
            # TODO: parse inbound client messages (e.g. user interjecting a new
            # instruction into a running agent) and dispatch to run_service.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
