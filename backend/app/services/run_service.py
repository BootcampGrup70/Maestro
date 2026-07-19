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

from app.core import tasks
from app.core.concurrency import get_run_semaphore
from app.core.time import now_ms
from app.db import SessionLocal
from app.models.agent import Agent
from app.models.enums import AgentStatus, MessageRole, RunStatus
from app.models.message import Message
from app.models.run import Run
from app.services import agent_service, ollama_client
from app.services.tools.registry import TOOL_SCHEMAS
from app.ws import events
from app.ws.manager import ConnectionManager, get_manager

logger = logging.getLogger(__name__)


async def _next_seq(session: AsyncSession, agent_id: str) -> int:
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


async def _queue_run(session: AsyncSession, agent: Agent, prompt: str) -> Run:
    """Create a queued ``Run`` row and spawn its background executor.

    Shared by ``create_run`` (new user prompt) and ``restart_run`` (retry an existing,
    already-persisted prompt) -- neither touches message history here.
    """
    run = Run(agent_id=agent.id, prompt=prompt, status=RunStatus.QUEUED)
    session.add(run)
    await session.commit()
    await session.refresh(run)

    await agent_service.set_status(session, agent, AgentStatus.QUEUED)
    await get_manager().broadcast(events.agent_status(agent.id, AgentStatus.QUEUED))

    # Fire-and-forget: the executor opens its own session (outside request scope). The
    # task is registered so a later cancel request can find and stop it.
    task = asyncio.create_task(_execute_run(run.id, agent.id))
    tasks.register(agent.id, task)
    return run


async def create_run(session: AsyncSession, agent: Agent, prompt: str) -> Run:
    """Persist the user prompt + a queued run, then spawn the background executor."""
    await _persist_message(session, agent.id, MessageRole.USER, prompt)
    return await _queue_run(session, agent, prompt)


async def _last_run(session: AsyncSession, agent_id: str) -> Run | None:
    result = await session.execute(
        select(Run).where(Run.agent_id == agent_id).order_by(Run.started_at.desc()).limit(1)
    )
    return result.scalars().first()


async def restart_run(session: AsyncSession, agent: Agent) -> Run:
    """Retry an agent left in ``error``.

    Reuses the last run's prompt -- already persisted as an (unanswered) user message
    when that run was first created -- without adding a duplicate user turn.
    """
    if agent.status != AgentStatus.ERROR:
        raise ValueError("Agent is not in an error state")
    last_run = await _last_run(session, agent.id)
    if last_run is None:
        raise ValueError("Agent has no previous run to restart")
    return await _queue_run(session, agent, last_run.prompt)


def cancel_run(agent_id: str) -> bool:
    """Cancel the agent's in-flight run, if any. Returns False if none is active."""
    return tasks.cancel(agent_id)


async def restart_tree(session: AsyncSession, agent: Agent) -> list[Run]:
    """Restart ``agent`` and every descendant of it currently in ``error``, together.

    Descendants land in ``error`` (rather than ``idle``) when a crashing parent cascades
    a stop to them -- see ``_cascade_stop_children`` -- specifically so this can find and
    retry them via the same ``restart_run`` path as a standalone agent.
    """
    targets = [agent] if agent.status == AgentStatus.ERROR else []
    descendants = await agent_service.list_descendants(session, agent.id)
    targets.extend(child for child in descendants if child.status == AgentStatus.ERROR)
    if not targets:
        raise ValueError("No agent in this tree is in an error state")
    return [await restart_run(session, target) for target in targets]


async def _cascade_stop_children(manager: ConnectionManager, agent_id: str) -> None:
    """When ``agent_id``'s run crashes, stop every descendant's in-flight run too and
    flip it to ``error`` so the whole subtree becomes restart-eligible together.

    Each child is cancelled through the normal single-agent cancel path first (which
    settles it to ``idle`` + a ``cancelled`` run) and only re-stamped ``error`` *after*
    that finishes, so our stamp isn't clobbered by the child's own cleanup landing later.
    """
    async with SessionLocal() as session:
        descendants = await agent_service.list_descendants(session, agent_id)

    message = f"Stopped: parent agent {agent_id} failed"
    for child in descendants:
        task = tasks.get(child.id)
        if task is None or task.done():
            continue
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001 - one child's cleanup failing shouldn't stop the cascade
            logger.exception("Error while cascading stop to agent %s", child.id)

        async with SessionLocal() as session:
            fresh_child = await session.get(Agent, child.id)
            if fresh_child is None:
                continue
            await agent_service.set_status(
                session, fresh_child, AgentStatus.ERROR, error_message=message
            )
        await manager.broadcast(
            events.agent_status(child.id, AgentStatus.ERROR, error_message=message)
        )


async def _execute_run(run_id: str, agent_id: str) -> None:
    """Background task: stream the model output and persist the result."""
    manager = get_manager()
    semaphore = get_run_semaphore()

    try:
        await _run_inner(manager, semaphore, run_id, agent_id)
    except asyncio.CancelledError:
        await _mark_cancelled(manager, run_id, agent_id)
        raise
    finally:
        current_task = asyncio.current_task()
        if current_task is not None:
            tasks.unregister(agent_id, current_task)


async def _mark_cancelled(manager: ConnectionManager, run_id: str, agent_id: str) -> None:
    """Persist + broadcast a cancellation, but only if the run was still in flight.

    A cancel request racing with normal completion must not clobber a run that already
    finished (done/error) by the time this runs.
    """
    async with SessionLocal() as session:
        run = await session.get(Run, run_id)
        agent = await session.get(Agent, agent_id)
        if run is None or run.status not in (RunStatus.QUEUED, RunStatus.RUNNING):
            return
        run.status = RunStatus.CANCELLED
        run.finished_at = now_ms()
        session.add(run)
        await session.commit()
        if agent is not None:
            # Cancellation is a user action, not a failure, so the agent goes back to
            # `idle` (one of the fixed statuses the UI knows about) rather than `error`.
            await agent_service.set_status(session, agent, AgentStatus.IDLE)
        await manager.broadcast(events.run_finished(agent_id, run_id, RunStatus.CANCELLED.value))
        await manager.broadcast(events.agent_status(agent_id, AgentStatus.IDLE))


async def _run_inner(
    manager: ConnectionManager, semaphore: asyncio.Semaphore, run_id: str, agent_id: str
) -> None:
    async with semaphore:
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
                await _cascade_stop_children(manager, agent_id)


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
