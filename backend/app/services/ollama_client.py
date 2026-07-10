"""Thin async wrapper around the official ``ollama`` client.

Exposes a single ``stream_chat`` coroutine that yields normalized chunks so the rest of
the app never depends on Ollama's response shape directly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from ollama import AsyncClient

from app.config import get_settings


@dataclass
class ChatChunk:
    """One streamed step from the model."""

    content: str = ""
    thinking: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False


@lru_cache
def get_client() -> AsyncClient:
    """Return a cached Ollama async client pointed at the configured host."""
    return AsyncClient(host=get_settings().ollama_host)


async def stream_chat(
    model: str,
    messages: Sequence[dict[str, Any]],
    *,
    options: dict[str, Any] | None = None,
    tools: Sequence[dict[str, Any]] | None = None,
    think: bool = False,
) -> AsyncIterator[ChatChunk]:
    """Stream a chat completion, yielding a ``ChatChunk`` per response step.

    Args:
        model: Ollama model name (e.g. ``llama3``).
        messages: Chat history as ``{"role", "content"}`` dicts.
        options: Model params (temperature, num_ctx, ...) from the agent's settings.
        tools: Tool schemas to advertise to the model.
        think: Enable reasoning output for models that support it.
    """
    client = get_client()
    stream = await client.chat(
        model=model,
        messages=list(messages),
        stream=True,
        options=options or {},
        tools=list(tools) if tools else None,
        think=think,
    )
    async for part in stream:
        msg = part.get("message", {}) if isinstance(part, dict) else part.message
        content = (msg.get("content") if isinstance(msg, dict) else msg.content) or ""
        thinking = (msg.get("thinking") if isinstance(msg, dict) else getattr(msg, "thinking", None)) or ""
        raw_tool_calls = (
            msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)
        ) or []
        done = bool(part.get("done") if isinstance(part, dict) else getattr(part, "done", False))
        tool_calls = [
            tc if isinstance(tc, dict) else tc.model_dump() for tc in raw_tool_calls
        ]
        yield ChatChunk(content=content, thinking=thinking, tool_calls=tool_calls, done=done)
