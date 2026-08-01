"""``library_agents`` table (Neon) — agent snapshots inside a workflow package.

Each row stores one agent's configuration within a published workflow. The
``local_ref`` / ``parent_local_ref`` fields preserve the parent-child tree
without depending on real agent IDs (which are regenerated on every import).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Column, Text
from sqlmodel import JSON, Field, SQLModel

from app.core.ids import new_id


class LibraryAgent(SQLModel, table=True):
    __tablename__ = "library_agents"

    id: str = Field(default_factory=new_id, primary_key=True)

    workflow_id: str = Field(foreign_key="library_workflows.id", index=True)

    name: str
    model: str
    system_prompt: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    settings: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))

    canvas_x: float = Field(default=0.0)
    canvas_y: float = Field(default=0.0)

    # Workflow-internal reference for preserving parent-child relationships.
    # Example: local_ref="A", another agent has parent_local_ref="A" → child of this one.
    local_ref: str = Field(default="")
    parent_local_ref: str | None = Field(default=None)
