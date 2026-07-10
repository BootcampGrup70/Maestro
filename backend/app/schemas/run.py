"""Run request/response DTOs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.enums import RunStatus


class RunCreate(BaseModel):
    prompt: str


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    prompt: str
    status: RunStatus
    started_at: int | None
    finished_at: int | None
