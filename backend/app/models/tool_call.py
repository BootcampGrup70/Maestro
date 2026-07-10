"""``tool_calls`` table - invocations of the shared filesystem tool (RUNTIME group)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Column, ForeignKey, Index, Text
from sqlmodel import JSON, Field, SQLModel

from app.core.ids import new_id
from app.core.time import now_ms
from app.models.enums import ToolCallStatus, ToolOperation, enum_type


class ToolCall(SQLModel, table=True):
    __tablename__ = "tool_calls"
    __table_args__ = (Index("idx_tool_calls_agent", "agent_id"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    agent_id: str = Field(
        sa_column=Column(
            Text,
            ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    # Assistant turn that triggered the call; detached (SET NULL) if the message is removed.
    message_id: str | None = Field(
        default=None,
        sa_column=Column(
            Text,
            ForeignKey("messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    tool_name: str = Field(default="filesystem")
    operation: ToolOperation = Field(
        sa_column=Column(enum_type(ToolOperation, "ck_tool_calls_operation"), nullable=False),
    )
    arguments: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    result: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    status: ToolCallStatus = Field(
        default=ToolCallStatus.PENDING,
        sa_column=Column(enum_type(ToolCallStatus, "ck_tool_calls_status"), nullable=False),
    )
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: int = Field(default_factory=now_ms)
