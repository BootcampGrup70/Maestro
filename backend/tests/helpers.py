"""Shared helpers for async, in-process API tests (see conftest.async_client)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from httpx import AsyncClient


async def create_agent(
    client: AsyncClient, name: str, model: str = "fake-model", parent_id: str | None = None
) -> str:
    payload = {"name": name, "model": model}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    response = await client.post("/api/agents", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def agent_status(client: AsyncClient, agent_id: str) -> str:
    response = await client.get(f"/api/agents/{agent_id}")
    assert response.status_code == 200
    return response.json()["status"]


async def wait_for(
    condition: Callable[[], bool | Awaitable[bool]],
    timeout: float = 3.0,
    interval: float = 0.02,
) -> None:
    """Poll ``condition`` (sync or async) until it's truthy, or raise on timeout."""

    async def _poll() -> None:
        while True:
            result = condition()
            if asyncio.iscoroutine(result):
                result = await result
            if result:
                return
            await asyncio.sleep(interval)

    await asyncio.wait_for(_poll(), timeout=timeout)
