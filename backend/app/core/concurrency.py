"""Global concurrency gate for agent runs.

README specifies at most 2 Ollama models/agents running at once. We enforce that with
a single process-wide semaphore acquired by ``run_service`` before it starts streaming.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache

from app.config import get_settings


@lru_cache
def get_run_semaphore() -> asyncio.Semaphore:
    """Return the process-wide semaphore limiting concurrent runs."""
    return asyncio.Semaphore(get_settings().max_concurrent_runs)


# Per-agent locks serialize runs of the *same* agent (the global semaphore only caps the
# total, so without this two runs for one agent could stream concurrently and interleave
# their messages). Acquired outside the semaphore in run_service. Bounded by agent count;
# no cleanup needed for v1.
_agent_locks: dict[str, asyncio.Lock] = {}


def get_agent_lock(agent_id: str) -> asyncio.Lock:
    """Return the process-wide lock serializing runs for a single agent."""
    lock = _agent_locks.get(agent_id)
    if lock is None:
        lock = _agent_locks[agent_id] = asyncio.Lock()
    return lock
