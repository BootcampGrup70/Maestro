"""``runs`` table - active/last task tracking per agent (RUNTIME group).

Tracks the current/last execution so a restart knows what to replay and so the
``queued``/``running`` states are explicit.
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Text
from sqlmodel import Field, SQLModel

from app.core.ids import new_id
from app.models.enums import RunStatus, enum_type


class Run(SQLModel, table=True):
    __tablename__ = "runs"
    __table_args__ = (
        # Fetch the latest run per agent.
        Index("idx_runs_agent_started", "agent_id", "started_at"),
    )

    id: str = Field(default_factory=new_id, primary_key=True)
    agent_id: str = Field(
        sa_column=Column(
            Text,
            ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    prompt: str
    status: RunStatus = Field(
        default=RunStatus.QUEUED,
        sa_column=Column(enum_type(RunStatus, "ck_runs_status"), nullable=False),
    )
    started_at: int | None = Field(default=None)
    finished_at: int | None = Field(default=None)
