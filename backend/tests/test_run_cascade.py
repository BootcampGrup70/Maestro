"""Verifies parent-crash cascade + tree restart:

- ``agent_service.list_descendants`` walks the whole subtree (children, grandchildren).
- When a parent's run crashes, its children's in-flight runs are stopped and the
  children land on ``error`` (not ``idle``) so the whole subtree is restart-eligible.
- ``POST /agents/{id}/restart-tree`` restarts the parent + every erroring descendant
  together, in one action.
"""

from __future__ import annotations

import asyncio

from httpx import AsyncClient

from app.db import SessionLocal
from app.services import agent_service, ollama_client
from app.services.ollama_client import ChatChunk
from tests.helpers import agent_status, create_agent, wait_for


async def test_list_descendants_includes_grandchildren(async_client: AsyncClient) -> None:
    root_id = await create_agent(async_client, "root")
    child_id = await create_agent(async_client, "child", parent_id=root_id)
    grandchild_id = await create_agent(async_client, "grandchild", parent_id=child_id)

    async with SessionLocal() as session:
        descendants = await agent_service.list_descendants(session, root_id)

    assert {agent.id for agent in descendants} == {child_id, grandchild_id}


async def test_parent_crash_cascades_stop_and_restart_tree_recovers_both(
    async_client: AsyncClient, monkeypatch
) -> None:
    parent_calls = 0
    child_calls = 0
    child_gate = asyncio.Event()

    async def fake_stream_chat(model, messages, *, options=None, tools=None, think=False):
        nonlocal parent_calls, child_calls
        if model == "parent-model":
            parent_calls += 1
            if parent_calls == 1:
                raise RuntimeError("parent crashed")
            yield ChatChunk(content="parent-ok", done=True)
            return

        child_calls += 1
        if child_calls == 1:
            await child_gate.wait()
            yield ChatChunk(content="child-first", done=True)
        else:
            yield ChatChunk(content="child-retry", done=True)

    monkeypatch.setattr(ollama_client, "stream_chat", fake_stream_chat)

    parent_id = await create_agent(async_client, "parent", model="parent-model")
    child_id = await create_agent(async_client, "child", model="child-model", parent_id=parent_id)

    # Get the child mid-flight (holding a semaphore slot) before the parent crashes.
    response = await async_client.post(f"/api/agents/{child_id}/runs", json={"prompt": "hi"})
    assert response.status_code == 202, response.text

    async def _child_thinking() -> bool:
        return await agent_status(async_client, child_id) == "thinking"

    await wait_for(_child_thinking)

    response = await async_client.post(f"/api/agents/{parent_id}/runs", json={"prompt": "go"})
    assert response.status_code == 202, response.text

    # The cascade re-stamps the child `error` as its last step, so waiting for that also
    # confirms the parent's own error handling (which runs first) is done too.
    async def _child_errored() -> bool:
        return await agent_status(async_client, child_id) == "error"

    await wait_for(_child_errored)
    assert await agent_status(async_client, parent_id) == "error"

    child_runs = (await async_client.get(f"/api/agents/{child_id}/runs")).json()
    assert len(child_runs) == 1
    assert child_runs[0]["status"] == "cancelled"

    child_agent = (await async_client.get(f"/api/agents/{child_id}")).json()
    assert str(parent_id) in child_agent["error_message"]

    # One action restarts both.
    response = await async_client.post(f"/api/agents/{parent_id}/restart-tree")
    assert response.status_code == 202, response.text
    assert len(response.json()) == 2

    async def _both_done() -> bool:
        return (
            await agent_status(async_client, parent_id) == "done"
            and await agent_status(async_client, child_id) == "done"
        )

    await wait_for(_both_done)
    assert parent_calls == 2
    assert child_calls == 2

    assert len((await async_client.get(f"/api/agents/{parent_id}/runs")).json()) == 2
    assert len((await async_client.get(f"/api/agents/{child_id}/runs")).json()) == 2


async def test_restart_tree_without_any_error_returns_409(async_client: AsyncClient) -> None:
    parent_id = await create_agent(async_client, "healthy-parent")
    response = await async_client.post(f"/api/agents/{parent_id}/restart-tree")
    assert response.status_code == 409


async def test_restart_tree_missing_agent_returns_404(async_client: AsyncClient) -> None:
    response = await async_client.post("/api/agents/does-not-exist/restart-tree")
    assert response.status_code == 404
