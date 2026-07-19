"""Verifies POST /agents/{id}/cancel: an in-flight run stops, the run row lands on
``cancelled`` (not ``error``), the agent settles back to ``idle``, and the freed
semaphore slot is picked up by a run that was still queued behind it.
"""

from __future__ import annotations

import asyncio

from httpx import AsyncClient

from app.services import ollama_client
from app.services.ollama_client import ChatChunk
from tests.helpers import agent_status, create_agent, wait_for


async def test_cancel_stops_run_and_frees_slot_for_queued_run(
    async_client: AsyncClient, monkeypatch
) -> None:
    # Default MAESTRO_MAX_CONCURRENT_RUNS is 2, so a 3rd agent is needed to have anyone
    # actually sitting in `queued` behind the two that acquire the semaphore immediately.
    active = 0
    gate = asyncio.Event()

    async def fake_stream_chat(model, messages, *, options=None, tools=None, think=False):
        nonlocal active
        active += 1
        try:
            await gate.wait()
            yield ChatChunk(content="ok", done=True)
        finally:
            active -= 1

    monkeypatch.setattr(ollama_client, "stream_chat", fake_stream_chat)

    victim_id = await create_agent(async_client, "victim")
    other_id = await create_agent(async_client, "other-active")
    queued_id = await create_agent(async_client, "queued-behind")

    for agent_id in (victim_id, other_id, queued_id):
        response = await async_client.post(f"/api/agents/{agent_id}/runs", json={"prompt": "hi"})
        assert response.status_code == 202, response.text

    await wait_for(lambda: active == 2)
    assert await agent_status(async_client, victim_id) == "thinking"
    assert await agent_status(async_client, other_id) == "thinking"
    assert await agent_status(async_client, queued_id) == "queued"

    response = await async_client.post(f"/api/agents/{victim_id}/cancel")
    assert response.status_code == 202, response.text

    async def _victim_idle() -> bool:
        return await agent_status(async_client, victim_id) == "idle"

    await wait_for(_victim_idle)

    # The freed semaphore slot should now be picked up by the queued run.
    async def _queued_thinking() -> bool:
        return await agent_status(async_client, queued_id) == "thinking"

    await wait_for(_queued_thinking)

    runs_response = await async_client.get(f"/api/agents/{victim_id}/runs")
    assert runs_response.status_code == 200
    runs = runs_response.json()
    assert len(runs) == 1
    assert runs[0]["status"] == "cancelled"

    gate.set()

    async def _both_finished() -> bool:
        return (
            await agent_status(async_client, other_id) == "done"
            and await agent_status(async_client, queued_id) == "done"
        )

    await wait_for(_both_finished)


async def test_cancel_without_active_run_returns_409(async_client: AsyncClient) -> None:
    agent_id = await create_agent(async_client, "idle-agent")
    response = await async_client.post(f"/api/agents/{agent_id}/cancel")
    assert response.status_code == 409


async def test_cancel_missing_agent_returns_404(async_client: AsyncClient) -> None:
    response = await async_client.post("/api/agents/does-not-exist/cancel")
    assert response.status_code == 404
