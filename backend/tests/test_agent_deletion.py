"""Confirms deleting an agent cascades to its messages/runs/tool_calls (database.md)."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
from sqlmodel import select

from app.db import SessionLocal
from app.models.enums import MessageRole, RunStatus, ToolOperation
from app.models.message import Message
from app.models.run import Run
from app.models.tool_call import ToolCall


def _create_agent(client: TestClient) -> str:
    response = client.post("/api/agents", json={"name": "Worker", "model": "llama3"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _seed_children(agent_id: str) -> None:
    """Insert one row per child table directly, bypassing the run pipeline."""
    async with SessionLocal() as session:
        message = Message(agent_id=agent_id, seq=0, role=MessageRole.USER, content="hi")
        session.add(message)
        await session.commit()
        await session.refresh(message)

        session.add(Run(agent_id=agent_id, prompt="hi", status=RunStatus.DONE))
        session.add(
            ToolCall(
                agent_id=agent_id,
                message_id=message.id,
                operation=ToolOperation.READ,
                arguments={"path": "a.txt"},
            )
        )
        await session.commit()


async def _child_counts(agent_id: str) -> tuple[int, int, int]:
    async with SessionLocal() as session:
        messages = (
            await session.execute(select(Message).where(Message.agent_id == agent_id))
        ).scalars().all()
        runs = (
            await session.execute(select(Run).where(Run.agent_id == agent_id))
        ).scalars().all()
        tool_calls = (
            await session.execute(select(ToolCall).where(ToolCall.agent_id == agent_id))
        ).scalars().all()
        return len(messages), len(runs), len(tool_calls)


async def _seed_active_run(agent_id: str, status: RunStatus) -> None:
    async with SessionLocal() as session:
        session.add(Run(agent_id=agent_id, prompt="working", status=status))
        await session.commit()


async def test_delete_agent_cascades_to_children(client: TestClient) -> None:
    agent_id = _create_agent(client)
    await _seed_children(agent_id)
    assert await _child_counts(agent_id) == (1, 1, 1)

    response = client.delete(f"/api/agents/{agent_id}")
    assert response.status_code == 204

    assert await _child_counts(agent_id) == (0, 0, 0)


async def test_delete_agent_blocked_while_run_queued(client: TestClient) -> None:
    agent_id = _create_agent(client)
    await _seed_active_run(agent_id, RunStatus.QUEUED)

    response = client.delete(f"/api/agents/{agent_id}")
    assert response.status_code == 409

    # Agent must survive the rejected delete.
    assert client.get(f"/api/agents/{agent_id}").status_code == 200


async def test_delete_agent_blocked_while_run_running(client: TestClient) -> None:
    agent_id = _create_agent(client)
    await _seed_active_run(agent_id, RunStatus.RUNNING)

    response = client.delete(f"/api/agents/{agent_id}")
    assert response.status_code == 409


async def test_delete_agent_allowed_once_run_finished(client: TestClient) -> None:
    agent_id = _create_agent(client)
    await _seed_active_run(agent_id, RunStatus.DONE)

    response = client.delete(f"/api/agents/{agent_id}")
    assert response.status_code == 204


def test_delete_agent_broadcasts_agent_deleted_event(client: TestClient) -> None:
    agent_id = _create_agent(client)

    with client.websocket_connect("/ws") as websocket:
        response = client.delete(f"/api/agents/{agent_id}")
        assert response.status_code == 204

        event = websocket.receive_json()
        assert event["type"] == "agent_deleted"
        assert event["agent_id"] == agent_id


def test_delete_agent_blocked_by_active_run_does_not_broadcast(client: TestClient) -> None:
    agent_id = _create_agent(client)
    asyncio.run(_seed_active_run(agent_id, RunStatus.RUNNING))

    with client.websocket_connect("/ws") as websocket:
        response = client.delete(f"/api/agents/{agent_id}")
        assert response.status_code == 409

        # Nudge the socket so a wrongly-sent broadcast would already be queued, then
        # confirm nothing arrives.
        other_agent_id = _create_agent(client)
        event = websocket.receive_json()
        assert event["type"] == "agent_status"
        assert event["agent_id"] == other_agent_id
