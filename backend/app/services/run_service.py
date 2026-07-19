"""Run orchestration - the vertical slice reference implementation.

Flow (see the plan's sequence diagram):
    create_run -> queued -> [background task] acquire semaphore -> running/thinking ->
    stream from Ollama (broadcast deltas) -> persist assistant message -> done/idle.

Errors at any stage flip the agent to ``error`` and the run to ``error`` and broadcast an
``error`` event.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.concurrency import get_agent_lock, get_run_semaphore
from app.core.time import now_ms
from app.db import SessionLocal
from app.models.agent import Agent
from app.models.enums import AgentStatus, MessageRole, RunStatus
from app.models.message import Message
from app.models.run import Run
from app.services import agent_service, ollama_client
from app.services.tools.registry import TOOL_SCHEMAS
from app.ws import events
from app.ws.manager import get_manager

logger = logging.getLogger(__name__)

# An agent in one of these states already has (or is about to have) a run streaming, so a
# freshly-created run queues behind it rather than overriding its visible status.
_BUSY_STATUSES = {AgentStatus.QUEUED, AgentStatus.THINKING, AgentStatus.TOOL_CALLING}


async def _next_seq(session: AsyncSession, agent_id: str) -> int:
    # TODO(v2): read-then-insert isn't locked across sessions, so an interjection persisted
    # from the WS handler while a run persists its reply could collide on the unique
    # (agent_id, seq) index. Fine under the single-user v1 assumption.
    result = await session.execute(
        select(func.coalesce(func.max(Message.seq), -1)).where(Message.agent_id == agent_id)
    )
    return int(result.scalar_one()) + 1


async def _persist_message(
    session: AsyncSession,
    agent_id: str,
    role: MessageRole,
    content: str | None,
    thinking: str | None = None,
) -> Message:
    message = Message(
        agent_id=agent_id,
        seq=await _next_seq(session, agent_id),
        role=role,
        content=content,
        thinking=thinking,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def _build_history(session: AsyncSession, agent: Agent) -> list[dict[str, Any]]:
    """Assemble the Ollama chat history from persisted messages (+ system prompt)."""
    messages: list[dict[str, Any]] = []
    if agent.system_prompt:
        messages.append({"role": MessageRole.SYSTEM.value, "content": agent.system_prompt})
    result = await session.execute(
        select(Message).where(Message.agent_id == agent.id).order_by(Message.seq)
    )
    for msg in result.scalars().all():
        if msg.role == MessageRole.SYSTEM:
            continue  # system prompt already prepended
        messages.append({"role": msg.role.value, "content": msg.content or ""})
    return messages


async def create_run(session: AsyncSession, agent: Agent, prompt: str) -> Run:
    """Persist the user prompt + a queued run, then spawn the background executor.

    If the agent is already busy (an interjection while a run streams), the new run is
    still created and dispatched, but we leave the current run's status visible — the
    per-agent lock in ``_execute_run`` makes this run wait, and it flips the agent to
    ``thinking`` only when it actually starts.
    """
    was_busy = agent.status in _BUSY_STATUSES

    await _persist_message(session, agent.id, MessageRole.USER, prompt)

    run = Run(agent_id=agent.id, prompt=prompt, status=RunStatus.QUEUED)
    session.add(run)
    await session.commit()
    await session.refresh(run)

    if not was_busy:
        await agent_service.set_status(session, agent, AgentStatus.QUEUED)
        await get_manager().broadcast(events.agent_status(agent.id, AgentStatus.QUEUED))

    # Fire-and-forget: the executor opens its own session (outside request scope).
    asyncio.create_task(_execute_run(run.id, agent.id))
    return run


async def interject(session: AsyncSession, agent_id: str, prompt: str) -> Run | None:
    """Queue a user instruction arriving over the WebSocket.

    Functionally the same as ``POST /runs``: it reuses ``create_run``, so if the agent is
    mid-run the new instruction runs after the current one finishes (per-agent lock);
    if idle it starts immediately. Returns ``None`` if the agent doesn't exist.
    """
    agent = await agent_service.get_agent(session, agent_id)
    if agent is None:
        return None
    return await create_run(session, agent, prompt)


async def _execute_run(run_id: str, agent_id: str) -> None:
    """Background task: stream the model output and persist the result."""
    manager = get_manager()
    semaphore = get_run_semaphore()

    # Acquire the per-agent lock *outside* the semaphore (consistent order everywhere, so
    # no deadlock): a run queued behind another run for the same agent waits here holding
    # no semaphore slot, then streams only once the earlier run has finished.
    async with get_agent_lock(agent_id), semaphore:
        async with SessionLocal() as session:
            agent = await session.get(Agent, agent_id)
            run = await session.get(Run, run_id)
            if agent is None or run is None:
                logger.warning("Run %s or agent %s vanished before execution", run_id, agent_id)
                return

            run.status = RunStatus.RUNNING
            run.started_at = now_ms()
            session.add(run)
            await session.commit()

            await agent_service.set_status(session, agent, AgentStatus.THINKING)
            await manager.broadcast(events.run_started(agent_id, run_id))
            await manager.broadcast(events.agent_status(agent_id, AgentStatus.THINKING))

            try:
                history = await _build_history(session, agent)
                content_parts: list[str] = []
                thinking_parts: list[str] = []
                pending_tool_calls: list[dict[str, Any]] = []

                async for chunk in ollama_client.stream_chat(
                    model=agent.model,
                    messages=history,
                    options=agent.settings,
                    tools=TOOL_SCHEMAS,
                    think=bool(agent.settings.get("think", False)),
                ):
                    if chunk.content:
                        content_parts.append(chunk.content)
                        await manager.broadcast(
                            events.message_delta(agent_id, run_id, chunk.content)
                        )
                    if chunk.thinking:
                        thinking_parts.append(chunk.thinking)
                        await manager.broadcast(
                            events.thinking_delta(agent_id, run_id, chunk.thinking)
                        )
                    if chunk.tool_calls:
                        pending_tool_calls.extend(chunk.tool_calls)

                message = await _persist_message(
                    session,
                    agent_id,
                    MessageRole.ASSISTANT,
                    content="".join(content_parts) or None,
                    thinking="".join(thinking_parts) or None,
                )
                await manager.broadcast(
                    events.message_created(agent_id, message.id, message.seq, message.role.value)
                )

                if pending_tool_calls:
                    # TODO(team): execute tool calls, persist tool_calls rows, feed results
                    # back to the model, and continue the loop until no tool calls remain.
                    await _handle_tool_calls(session, agent, message, pending_tool_calls)

                run.status = RunStatus.DONE
                run.finished_at = now_ms()
                session.add(run)
                await session.commit()

                await agent_service.set_status(session, agent, AgentStatus.DONE)
                await manager.broadcast(
                    events.run_finished(agent_id, run_id, RunStatus.DONE.value)
                )
                await manager.broadcast(events.agent_status(agent_id, AgentStatus.DONE))

            except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
                logger.exception("Run %s failed", run_id)
                run.status = RunStatus.ERROR
                run.finished_at = now_ms()
                session.add(run)
                await session.commit()
                await agent_service.set_status(
                    session, agent, AgentStatus.ERROR, error_message=str(exc)
                )
                await manager.broadcast(
                    events.run_finished(agent_id, run_id, RunStatus.ERROR.value)
                )
                await manager.broadcast(
                    events.agent_status(agent_id, AgentStatus.ERROR, error_message=str(exc))
                )
                await manager.broadcast(events.error(agent_id, str(exc)))


async def _handle_tool_calls(
    session: AsyncSession,
    agent: Agent,
    message: Message,
    tool_calls: list[dict[str, Any]],
) -> None:
    """STUB: execute filesystem tool calls requested by the model.

    Open task for the team. The intended implementation:
      1. Flip agent status to ``tool_calling`` and broadcast it.
      2. For each tool call: insert a ``tool_calls`` row (status=pending, broadcast
         tool_call_created), dispatch via ``services.tools.registry.dispatch``, then update
         the row (success/error, result/error_message, broadcast tool_call_updated).
      3. Append a ``tool`` role message with each result and re-invoke the model so it can
         continue, looping until no more tool calls are returned.
    See app/services/tools/filesystem.py and registry.py for the ready-made helpers.

    For now this is a no-op (logs and returns) so the vertical slice still completes; the
    model's tool requests are simply not executed yet.
    """
    logger.info(
        "Agent %s requested %d tool call(s); tool execution is not yet implemented",
        agent.id,
        len(tool_calls),
    )


async def list_runs(session: AsyncSession, agent_id: str) -> list[Run]:
    result = await session.execute(
        select(Run).where(Run.agent_id == agent_id).order_by(Run.started_at.desc())
    )
    return list(result.scalars().all())
