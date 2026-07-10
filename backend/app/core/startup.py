"""Startup normalization of stale runtime state (see database.md).

On boot no agent process is actually running, so we reconcile the DB with reality before
serving requests: stale live-status agents become ``idle`` and any unfinished run becomes
``error``. Agents left in ``error``/``done`` are preserved so the user can act on them.
"""

from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import now_ms
from app.models.agent import Agent
from app.models.enums import AgentStatus, RunStatus
from app.models.run import Run


async def normalize_stale_state(session: AsyncSession) -> None:
    """Reset stale live agent statuses and unfinished runs."""
    await session.execute(
        update(Agent)
        .where(
            Agent.status.in_(
                [AgentStatus.THINKING, AgentStatus.TOOL_CALLING, AgentStatus.QUEUED]
            )
        )
        .values(status=AgentStatus.IDLE, updated_at=now_ms())
    )
    await session.execute(
        update(Run)
        .where(Run.status.in_([RunStatus.QUEUED, RunStatus.RUNNING]))
        .values(status=RunStatus.ERROR, finished_at=now_ms())
    )
    await session.commit()
