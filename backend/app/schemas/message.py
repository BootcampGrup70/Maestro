"""Message response DTOs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.enums import MessageRole


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    seq: int
    role: MessageRole
    content: str | None
    thinking: str | None
    created_at: int
