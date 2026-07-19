"""Registry of in-flight run tasks, keyed by agent id.

``asyncio.create_task`` alone gives no way to look a task back up later (see
``run_service.create_run``), so cancelling a run needs somewhere to record which
``Task`` is currently executing which agent's run.
"""

from __future__ import annotations

import asyncio

_running_tasks: dict[str, asyncio.Task] = {}


def register(agent_id: str, task: asyncio.Task) -> None:
    """Record ``task`` as the in-flight run for ``agent_id``."""
    _running_tasks[agent_id] = task


def unregister(agent_id: str, task: asyncio.Task) -> None:
    """Remove the registration, but only if it still points at ``task``.

    A newer run for the same agent may have already registered its own task by the
    time this one's cleanup runs; guard against clobbering that newer entry.
    """
    if _running_tasks.get(agent_id) is task:
        del _running_tasks[agent_id]


def get(agent_id: str) -> asyncio.Task | None:
    """Return the agent's in-flight run task, if any."""
    return _running_tasks.get(agent_id)


def cancel(agent_id: str) -> bool:
    """Request cancellation of the agent's in-flight run.

    Returns False if there is no active (registered, not-yet-done) task for the agent.
    """
    task = _running_tasks.get(agent_id)
    if task is None or task.done():
        return False
    task.cancel()
    return True


def reset_for_tests() -> list[asyncio.Task]:
    """Clear the registry and return whatever tasks were still tracked.

    Test-only: lets a test suite drain/cancel leftover tasks between tests so they can't
    leak into the next test's (process-wide) semaphore/registry state.
    """
    leftover = list(_running_tasks.values())
    _running_tasks.clear()
    return leftover
