"""``agents`` table - canvas nodes (DEFINITION group). Mirrors database.md."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Column, ForeignKey, Index, Text
from sqlmodel import JSON, Field, SQLModel

from app.core.ids import new_id
from app.core.time import now_ms
from app.models.enums import AgentStatus, enum_type


class Agent(SQLModel, table=True):
    __tablename__ = "agents"
    __table_args__ = (Index("idx_agents_parent", "parent_id"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    name: str
    model: str
    system_prompt: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    settings: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    status: AgentStatus = Field(
        default=AgentStatus.IDLE,
        sa_column=Column(enum_type(AgentStatus, "ck_agents_status"), nullable=False),
    )
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # Self-referencing hierarchy FK; ON DELETE SET NULL detaches children (unused in v1).
    parent_id: str | None = Field(
        default=None,
        sa_column=Column(
            Text,
            ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    canvas_x: float = Field(default=0.0)
    canvas_y: float = Field(default=0.0)
    created_at: int = Field(default_factory=now_ms)
    updated_at: int = Field(default_factory=now_ms)
