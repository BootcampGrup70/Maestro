"""The ``/ws`` WebSocket endpoint — the single bidirectional live channel.

On connect the client receives an ``agent_snapshot`` of every agent's current status, then
the server streams run events (broadcast from the run pipeline). Inbound frames let the
user interject a new instruction into an agent (queued after any in-flight run); malformed
frames get an ``error`` reply without dropping the socket.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.db import SessionLocal
from app.schemas.ws import parse_inbound
from app.services import agent_service, run_service
from app.ws import events
from app.ws.manager import get_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    manager = get_manager()
    await manager.connect(websocket)

    # Snapshot current agent statuses so a fresh client renders live state immediately.
    async with SessionLocal() as session:
        agents = await agent_service.list_agents(session)
    await manager.send_personal(websocket, events.agent_snapshot(agents))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = parse_inbound(raw)
            except (ValidationError, ValueError) as exc:
                await manager.send_personal(
                    websocket, events.error(None, f"Invalid inbound message: {exc}")
                )
                continue

            # Only interject exists today; open a fresh session per op (the socket is
            # long-lived, so we don't hold one session for its whole lifetime).
            async with SessionLocal() as session:
                run = await run_service.interject(session, message.agent_id, message.prompt)
            if run is None:
                await manager.send_personal(
                    websocket,
                    events.error(message.agent_id, f"Unknown agent: {message.agent_id}"),
                )
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
