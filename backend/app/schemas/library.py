"""Library request/response DTOs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Nested agent inside a workflow ────────────────────────────────────────

class LibraryAgentData(BaseModel):
    """Agent config used when publishing a workflow (input)."""

    name: str
    model: str
    system_prompt: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    canvas_x: float = 0.0
    canvas_y: float = 0.0
    local_ref: str                          # e.g. "A", "B", "C"
    parent_local_ref: str | None = None     # e.g. "A" means child of ref "A"


class LibraryAgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: str
    name: str
    model: str
    system_prompt: str | None
    settings: dict[str, Any]
    canvas_x: float
    canvas_y: float
    local_ref: str
    parent_local_ref: str | None


# ── Workflow (the package) ────────────────────────────────────────────────

class WorkflowPublish(BaseModel):
    """Publish a workflow to the library.

    Can provide agents explicitly OR pass agent_ids to snapshot from local DB.
    """

    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)

    # Option 1: explicit agent configs
    agents: list[LibraryAgentData] = Field(default_factory=list)

    # Option 2: snapshot from local canvas (list of local agent IDs)
    agent_ids: list[str] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    """Partial update for a workflow's metadata."""

    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class WorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    tags: list[str]
    agent_count: int
    import_count: int
    created_at: int
    updated_at: int


class WorkflowDetailRead(WorkflowRead):
    """Workflow with its agent list included."""

    agents: list[LibraryAgentRead] = Field(default_factory=list)


class WorkflowImport(BaseModel):
    """Import a workflow from the library to the local canvas."""

    offset_x: float = 0.0   # shift all agent positions by this amount
    offset_y: float = 0.0
