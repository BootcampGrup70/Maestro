"""WebSocket message schemas — the frontend contract for the ``/ws`` channel.

**Outbound** events pushed to clients are a JSON object of shape::

    { "type": <WSEventType>, "agent_id": <str|null>, "data": <object>, "ts": <epoch_ms> }

**Inbound** frames sent by the client are parsed with :func:`parse_inbound` into one of the
``WSInboundType`` models (currently only ``interject``).
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, TypeAdapter

from app.core.time import now_ms


class WSEventType(str, Enum):
    AGENT_STATUS = "agent_status"
    AGENT_SNAPSHOT = "agent_snapshot"
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


class WSInboundType(str, Enum):
    INTERJECT = "interject"


class InterjectMessage(BaseModel):
    """User interjects a new instruction into an agent's conversation.

    Queued after any in-flight run for that agent (see ``run_service.interject``).
    """

    type: Literal[WSInboundType.INTERJECT]
    agent_id: str
    prompt: str


# Only one inbound frame type today. When a second is added, turn this into a
# ``Annotated[Union[InterjectMessage, ...], Field(discriminator="type")]`` so ``type``
# selects the model.
WSInboundMessage = InterjectMessage

_INBOUND_ADAPTER: TypeAdapter[WSInboundMessage] = TypeAdapter(WSInboundMessage)


def parse_inbound(raw: str) -> InterjectMessage:
    """Parse and validate a raw inbound WS text frame.

    Raises ``ValueError`` on malformed JSON and ``pydantic.ValidationError`` on an
    unknown ``type`` or missing/invalid fields; the endpoint turns either into an
    ``error`` event without dropping the socket.
    """
    return _INBOUND_ADAPTER.validate_python(json.loads(raw))
