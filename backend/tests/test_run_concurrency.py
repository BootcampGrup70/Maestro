"""Verifies the Semaphore(2) concurrency gate (``app/core/concurrency.py``).

A 3rd concurrently-started run must stay ``queued`` until one of the first two frees a
slot, and at no point may more than ``MAESTRO_MAX_CONCURRENT_RUNS`` runs be inside the
model call at once. ``ollama_client.stream_chat`` is replaced with a gated fake so the
test is fast and fully deterministic.
"""

from __future__ import annotations

import asyncio

from httpx import AsyncClient

from app.services import ollama_client
from app.services.ollama_client import ChatChunk
from tests.helpers import agent_status, create_agent, wait_for


async def test_semaphore_limits_to_two_concurrent_runs(
    async_client: AsyncClient, monkeypatch
) -> None:
    active = 0
    max_active = 0
    gate = asyncio.Event()

    async def fake_stream_chat(model, messages, *, options=None, tools=None, think=False):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        try:
            await gate.wait()
            yield ChatChunk(content="ok", done=True)
        finally:
            active -= 1

    monkeypatch.setattr(ollama_client, "stream_chat", fake_stream_chat)

    agent_ids = [await create_agent(async_client, f"agent-{i}") for i in range(3)]
    for agent_id in agent_ids:
        response = await async_client.post(f"/api/agents/{agent_id}/runs", json={"prompt": "hi"})
        assert response.status_code == 202, response.text

    # Exactly two runs should make it into the (mocked) model call...
    await wait_for(lambda: active == 2)
    # ...and give the loop a moment to prove a third isn't slipping in behind them.
    await asyncio.sleep(0.05)
    assert active == 2
    assert max_active == 2

    statuses = [await agent_status(async_client, agent_id) for agent_id in agent_ids]
    assert statuses.count("thinking") == 2
    assert statuses.count("queued") == 1

    # Release all three; the queued one should now acquire the freed slot and finish.
    gate.set()

    async def _all_done() -> bool:
        results = [await agent_status(async_client, agent_id) for agent_id in agent_ids]
        return all(status == "done" for status in results)

    await wait_for(_all_done)
    assert max_active == 2
