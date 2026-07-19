"""WebSocket tests: connect snapshot, inbound validation, and a mocked-Ollama interject.

The run pipeline uses process-wide singletons holding asyncio primitives (the manager's
lock, the run semaphore, per-agent locks). Each TestClient spins up its own event loop, so
we reset those caches per test to avoid an asyncio primitive binding to a stale loop.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core import concurrency
from app.services import run_service
from app.services.ollama_client import ChatChunk
from app.ws.manager import get_manager


@pytest.fixture(autouse=True)
def _reset_run_singletons() -> None:
    get_manager.cache_clear()
    concurrency.get_run_semaphore.cache_clear()
    concurrency._agent_locks.clear()


def _create_agent(client: TestClient, name: str = "Planner") -> dict:
    response = client.post(
        "/api/agents",
        json={"name": name, "model": "qwen3.5:4b", "settings": {}},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_snapshot_sent_on_connect(client: TestClient) -> None:
    agent = _create_agent(client)
    with client.websocket_connect("/ws") as ws:
        frame = ws.receive_json()
    assert frame["type"] == "agent_snapshot"
    snapshot = {a["agent_id"]: a for a in frame["data"]["agents"]}
    assert agent["id"] in snapshot
    assert snapshot[agent["id"]]["status"] == "idle"


def test_invalid_inbound_gets_error_and_keeps_socket_open(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "agent_snapshot"  # drain snapshot

        ws.send_text("not json")
        assert ws.receive_json()["type"] == "error"

        ws.send_json({"type": "bogus"})
        assert ws.receive_json()["type"] == "error"

        # Socket still alive: a well-formed frame for a missing agent still gets a reply.
        ws.send_json({"type": "interject", "agent_id": "nope", "prompt": "hi"})
        reply = ws.receive_json()
        assert reply["type"] == "error"
        assert "nope" in reply["data"]["message"]


def test_interject_starts_a_run(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_stream_chat(*_args, **_kwargs):
        yield ChatChunk(content="Hello", done=False)
        yield ChatChunk(content=" world", done=True)

    monkeypatch.setattr(run_service.ollama_client, "stream_chat", fake_stream_chat)

    agent = _create_agent(client)
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "agent_snapshot"  # drain snapshot

        ws.send_json({"type": "interject", "agent_id": agent["id"], "prompt": "hi"})

        types: list[str] = []
        deltas: list[str] = []
        for _ in range(20):
            frame = ws.receive_json()
            types.append(frame["type"])
            if frame["type"] == "message_delta":
                deltas.append(frame["data"]["delta"])
            if frame["type"] == "run_finished":
                break

    assert "run_started" in types
    assert "message_created" in types
    assert "run_finished" in types
    assert "".join(deltas) == "Hello world"
