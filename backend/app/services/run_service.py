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
from app.ws.manager import get_manager

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


async def create_run(session: AsyncSession, agent: Agent, prompt: str) -> Run:
    """Persist the user prompt + a queued run, then spawn the background executor."""
    await _persist_message(session, agent.id, MessageRole.USER, prompt)

    run = Run(agent_id=agent.id, prompt=prompt, status=RunStatus.QUEUED)
    session.add(run)
    await session.commit()
    await session.refresh(run)

    await agent_service.set_status(session, agent, AgentStatus.QUEUED)
    await get_manager().broadcast(events.agent_status(agent.id, AgentStatus.QUEUED))

    # Fire-and-forget: the executor opens its own session (outside request scope).
    asyncio.create_task(_execute_run(run.id, agent.id))
    return run


async def _execute_run(run_id: str, agent_id: str) -> None:
    """Background task: stream the model output and persist the result."""
    manager = get_manager()
    semaphore = get_run_semaphore()

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


async def _handle_tool_calls(
    session: AsyncSession,
    agent: Agent,
    message: Message,
    tool_calls: list[dict[str, Any]],
) -> None:
    """Tool-calling lifecycle: execute tools, persist results, re-invoke model until done."""
    from app.models.tool_call import ToolCall
    from app.models.enums import ToolCallStatus
    from app.services.tools.registry import dispatch
    from app.services.tools.filesystem import FilesystemToolError

    manager = get_manager()
    MAX_ITERATIONS = 10
    iteration = 0

    # Agent durumunu tool_calling yap
    await agent_service.set_status(session, agent, AgentStatus.TOOL_CALLING)
    await manager.broadcast(events.agent_status(agent.id, AgentStatus.TOOL_CALLING))

    current_tool_calls = tool_calls
    history = await _build_history(session, agent)

    while current_tool_calls and iteration < MAX_ITERATIONS:
        iteration += 1
        tool_messages: list[dict[str, Any]] = []

        for call in current_tool_calls:
            tool_name = call.get("function", {}).get("name", "filesystem")
            arguments = call.get("function", {}).get("arguments", {})
            operation = arguments.get("operation", "")

            # DB'ye pending olarak kaydet
            tc = ToolCall(
                agent_id=agent.id,
                message_id=message.id,
                tool_name=tool_name,
                operation=operation,
                arguments=arguments,
                status=ToolCallStatus.PENDING,
            )
            session.add(tc)
            await session.commit()
            await session.refresh(tc)

            await manager.broadcast(
                events.tool_call_created(agent.id, tc.id, operation)
            )

            # Tool'u çalıştır
            try:
                result = dispatch(tool_name, arguments)
                tc.status = ToolCallStatus.SUCCESS
                tc.result = result
            except (FilesystemToolError, Exception) as exc:
                result = str(exc)
                tc.status = ToolCallStatus.ERROR
                tc.error_message = result
                logger.warning("Tool call failed: %s", exc)

            session.add(tc)
            await session.commit()

            await manager.broadcast(
                events.tool_call_updated(agent.id, tc.id, tc.status.value)
            )

            # Modele geri dönecek mesajı hazırla
            tool_messages.append({
                "role": MessageRole.TOOL.value,
                "content": result,
            })

        # Tool sonuçlarını history'e ekle
        history.extend(tool_messages)

        # Modeli tekrar çağır
        content_parts: list[str] = []
        thinking_parts: list[str] = []
        current_tool_calls = []

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
                    events.message_delta(agent.id, None, chunk.content)
                )
            if chunk.thinking:
                thinking_parts.append(chunk.thinking)
            if chunk.tool_calls:
                current_tool_calls.extend(chunk.tool_calls)

        # Yeni mesajı kaydet
        if content_parts or thinking_parts:
            message = await _persist_message(
                session,
                agent.id,
                MessageRole.ASSISTANT,
                content="".join(content_parts) or None,
                thinking="".join(thinking_parts) or None,
            )
            await manager.broadcast(
                events.message_created(agent.id, message.id, message.seq, message.role.value)
            )

    if iteration >= MAX_ITERATIONS:
        logger.warning("Agent %s reached max tool-call iterations (%d)", agent.id, MAX_ITERATIONS)


async def list_runs(session: AsyncSession, agent_id: str) -> list[Run]:
    result = await session.execute(
        select(Run).where(Run.agent_id == agent_id).order_by(Run.started_at.desc())
    )
    return list(result.scalars().all())
