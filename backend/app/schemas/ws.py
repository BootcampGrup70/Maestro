"""WebSocket event envelope.

Every message pushed to clients is a JSON object of shape::

    { "type": <WSEventType>, "agent_id": <str|null>, "data": <object>, "ts": <epoch_ms> }
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.core.time import now_ms


class WSEventType(str, Enum):
    AGENT_STATUS = "agent_status"
    RUN_STARTED = "run_started"
    RUN_FINISHED = "run_finished"
    MESSAGE_CREATED = "message_created"
    MESSAGE_DELTA = "message_delta"
    THINKING_DELTA = "thinking_delta"
    TOOL_CALL_CREATED = "tool_call_created"
    TOOL_CALL_UPDATED = "tool_call_updated"
    ERROR = "error"


class WSEvent(BaseModel):
    type: WSEventType
    agent_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    ts: int = Field(default_factory=now_ms)
