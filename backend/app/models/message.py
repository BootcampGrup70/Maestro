"""``messages`` table - per-agent conversation history (RUNTIME group)."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Text
from sqlmodel import Field, SQLModel

from app.core.ids import new_id
from app.core.time import now_ms
from app.models.enums import MessageRole, enum_type


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    __table_args__ = (
        # Orders the thread and prevents duplicate slots per agent.
        Index("idx_messages_agent_seq", "agent_id", "seq", unique=True),
    )

    id: str = Field(default_factory=new_id, primary_key=True)
    agent_id: str = Field(
        sa_column=Column(
            Text,
            ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    # Monotonically increasing per agent; orders the conversation.
    seq: int
    role: MessageRole = Field(
        sa_column=Column(enum_type(MessageRole, "ck_messages_role"), nullable=False),
    )
    content: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # Reasoning/thought text for assistant turns; shown in the reasoning panel.
    thinking: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: int = Field(default_factory=now_ms)
