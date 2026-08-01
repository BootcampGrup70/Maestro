"""Tool call response DTOs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import ToolCallStatus, ToolOperation


class ToolCallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    message_id: str | None
    tool_name: str
    operation: ToolOperation
    arguments: dict[str, Any]
    result: str | None
    status: ToolCallStatus
    error_message: str | None
    created_at: int
