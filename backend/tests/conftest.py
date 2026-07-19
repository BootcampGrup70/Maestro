"""Test fixtures.

We point the app at a throwaway temp-file SQLite DB *before* importing it, so the
module-level engine (created at import time from settings) uses the test database rather
than the real ``maestro.db``.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

_TMP_DIR = Path(tempfile.mkdtemp(prefix="maestro-test-"))
os.environ["MAESTRO_DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DIR / 'test.db'}"
os.environ["MAESTRO_WORKSPACE_DIR"] = str(_TMP_DIR / "workspace")
os.environ["MAESTRO_AUTO_CREATE_TABLES"] = "1"

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.core import tasks
from app.core.concurrency import get_run_semaphore
from app.main import app, lifespan


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient that runs the app lifespan (creates tables on the temp DB)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    """An httpx.AsyncClient driving the app in-process, on the test's own event loop.

    Needed (instead of ``client``) whenever a test must interleave ``await`` with
    background tasks spawned via ``asyncio.create_task`` (e.g. run execution) - the sync
    TestClient runs the app on a separate portal thread/loop, which makes that kind of
    fine-grained interleaving impractical.
    """
    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture(autouse=True)
async def _cleanup_background_runs() -> AsyncIterator[None]:
    """Cancel + drain any run tasks a test leaves in flight.

    ``get_run_semaphore()`` and the task registry are process-wide singletons (not reset
    per test), so a task a failed assertion left dangling would otherwise leak into every
    later test's semaphore state.
    """
    yield
    leftover = tasks.reset_for_tests()
    for task in leftover:
        task.cancel()
    if leftover:
        await asyncio.gather(*leftover, return_exceptions=True)
    get_run_semaphore.cache_clear()
