"""Typed builders for the WebSocket events emitted by the run pipeline.

Keeping construction in one place means the frontend contract lives in a single module.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from app.models.enums import AgentStatus
from app.schemas.ws import WSEvent, WSEventType

if TYPE_CHECKING:
    from app.models.agent import Agent


def agent_status(agent_id: str, status: AgentStatus, error_message: str | None = None) -> WSEvent:
    return WSEvent(
        type=WSEventType.AGENT_STATUS,
        agent_id=agent_id,
        data={"status": status.value, "error_message": error_message},
    )


def agent_snapshot(agents: Iterable[Agent]) -> WSEvent:
    """A one-shot dump of every agent's current status, sent when a client connects.

    Agent-scoped fields live in ``data['agents']`` since this event spans all agents;
    the envelope's top-level ``agent_id`` stays ``None``.
    """
    return WSEvent(
        type=WSEventType.AGENT_SNAPSHOT,
        data={
            "agents": [
                {
                    "agent_id": agent.id,
                    "status": agent.status.value,
                    "error_message": agent.error_message,
                }
                for agent in agents
            ]
        },
    )


def run_started(agent_id: str, run_id: str) -> WSEvent:
    return WSEvent(type=WSEventType.RUN_STARTED, agent_id=agent_id, data={"run_id": run_id})


def run_finished(agent_id: str, run_id: str, status: str) -> WSEvent:
    return WSEvent(
        type=WSEventType.RUN_FINISHED,
        agent_id=agent_id,
        data={"run_id": run_id, "status": status},
    )


def message_delta(agent_id: str, run_id: str, delta: str) -> WSEvent:
    return WSEvent(
        type=WSEventType.MESSAGE_DELTA,
        agent_id=agent_id,
        data={"run_id": run_id, "delta": delta},
    )


def thinking_delta(agent_id: str, run_id: str, delta: str) -> WSEvent:
    return WSEvent(
        type=WSEventType.THINKING_DELTA,
        agent_id=agent_id,
        data={"run_id": run_id, "delta": delta},
    )


def message_created(agent_id: str, message_id: str, seq: int, role: str) -> WSEvent:
    return WSEvent(
        type=WSEventType.MESSAGE_CREATED,
        agent_id=agent_id,
        data={"message_id": message_id, "seq": seq, "role": role},
    )


def tool_call_created(agent_id: str, tool_call_id: str, operation: str) -> WSEvent:
    return WSEvent(
        type=WSEventType.TOOL_CALL_CREATED,
        agent_id=agent_id,
        data={"tool_call_id": tool_call_id, "operation": operation},
    )


def tool_call_updated(agent_id: str, tool_call_id: str, status: str) -> WSEvent:
    return WSEvent(
        type=WSEventType.TOOL_CALL_UPDATED,
        agent_id=agent_id,
        data={"tool_call_id": tool_call_id, "status": status},
    )


def error(agent_id: str | None, message: str) -> WSEvent:
    return WSEvent(type=WSEventType.ERROR, agent_id=agent_id, data={"message": message})
