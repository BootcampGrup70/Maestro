"""Verifies POST /agents/{id}/restart: retries an agent left in ``error`` using the last
run's already-persisted prompt, without adding a duplicate user message.
"""

from __future__ import annotations

from httpx import AsyncClient

from app.services import ollama_client
from app.services.ollama_client import ChatChunk
from tests.helpers import agent_status, create_agent, wait_for


async def test_restart_retries_last_prompt_without_duplicating_history(
    async_client: AsyncClient, monkeypatch
) -> None:
    call_count = 0

    async def fake_stream_chat(model, messages, *, options=None, tools=None, think=False):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("boom")
        yield ChatChunk(content="ok", done=True)

    monkeypatch.setattr(ollama_client, "stream_chat", fake_stream_chat)

    agent_id = await create_agent(async_client, "flaky")
    response = await async_client.post(f"/api/agents/{agent_id}/runs", json={"prompt": "hi"})
    assert response.status_code == 202, response.text

    async def _errored() -> bool:
        return await agent_status(async_client, agent_id) == "error"

    await wait_for(_errored)

    response = await async_client.post(f"/api/agents/{agent_id}/restart")
    assert response.status_code == 202, response.text
    assert response.json()["prompt"] == "hi"

    async def _done() -> bool:
        return await agent_status(async_client, agent_id) == "done"

    await wait_for(_done)
    assert call_count == 2

    runs_response = await async_client.get(f"/api/agents/{agent_id}/runs")
    assert runs_response.status_code == 200
    runs = runs_response.json()
    assert len(runs) == 2
    assert {run["status"] for run in runs} == {"error", "done"}

    messages_response = await async_client.get(f"/api/agents/{agent_id}/messages")
    assert messages_response.status_code == 200
    roles = [message["role"] for message in messages_response.json()]
    assert roles == ["user", "assistant"]


async def test_restart_requires_error_status(async_client: AsyncClient) -> None:
    agent_id = await create_agent(async_client, "idle-agent")
    response = await async_client.post(f"/api/agents/{agent_id}/restart")
    assert response.status_code == 409


async def test_restart_missing_agent_returns_404(async_client: AsyncClient) -> None:
    response = await async_client.post("/api/agents/does-not-exist/restart")
    assert response.status_code == 404
