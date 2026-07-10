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
