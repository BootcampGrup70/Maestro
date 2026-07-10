"""Agent request/response DTOs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AgentStatus


class AgentCreate(BaseModel):
    name: str
    model: str
    system_prompt: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    parent_id: str | None = None
    canvas_x: float = 0.0
    canvas_y: float = 0.0


class AgentUpdate(BaseModel):
    """Partial update. All fields optional; only provided ones are applied."""

    name: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    settings: dict[str, Any] | None = None
    canvas_x: float | None = None
    canvas_y: float | None = None


class AgentPositionUpdate(BaseModel):
    """Canvas position update (dragging a node)."""

    canvas_x: float
    canvas_y: float


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    model: str
    system_prompt: str | None
    settings: dict[str, Any]
    status: AgentStatus
    error_message: str | None
    parent_id: str | None
    canvas_x: float
    canvas_y: float
    created_at: int
    updated_at: int
