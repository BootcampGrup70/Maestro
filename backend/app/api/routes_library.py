"""Library endpoints — publish, browse, import, and manage shared workflows."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.neon_db import get_neon_session
from app.schemas.library import (
    LibraryAgentRead,
    WorkflowDetailRead,
    WorkflowImport,
    WorkflowPublish,
    WorkflowRead,
    WorkflowUpdate,
)
from app.services import library_service

router = APIRouter(prefix="/library", tags=["library"])


async def _get_or_404(neon: AsyncSession, workflow_id: str):
    wf = await library_service.get_workflow(neon, workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


# ── List / Search ─────────────────────────────────────────────────────────

@router.get("", response_model=list[WorkflowRead])
async def list_workflows(
    tag: str | None = Query(None, description="Filter by tag"),
    search: str | None = Query(None, description="Search name or description"),
    neon: AsyncSession = Depends(get_neon_session),
):
    return await library_service.list_workflows(neon, tag=tag, search=search)


# ── Publish ───────────────────────────────────────────────────────────────

@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def publish_workflow(
    data: WorkflowPublish,
    neon: AsyncSession = Depends(get_neon_session),
    local: AsyncSession = Depends(get_session),
):
    try:
        return await library_service.publish(neon, local, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Get Detail ────────────────────────────────────────────────────────────

@router.get("/{workflow_id}", response_model=WorkflowDetailRead)
async def get_workflow(
    workflow_id: str,
    neon: AsyncSession = Depends(get_neon_session),
):
    wf = await _get_or_404(neon, workflow_id)
    agents = await library_service.get_workflow_agents(neon, workflow_id)

    return WorkflowDetailRead(
        id=wf.id,
        name=wf.name,
        description=wf.description,
        tags=wf.tags,
        agent_count=wf.agent_count,
        import_count=wf.import_count,
        created_at=wf.created_at,
        updated_at=wf.updated_at,
        agents=[LibraryAgentRead.model_validate(a) for a in agents],
    )


# ── Update ────────────────────────────────────────────────────────────────

@router.patch("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    workflow_id: str,
    data: WorkflowUpdate,
    neon: AsyncSession = Depends(get_neon_session),
):
    wf = await _get_or_404(neon, workflow_id)
    return await library_service.update_workflow(neon, wf, data)


# ── Delete ────────────────────────────────────────────────────────────────

@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    neon: AsyncSession = Depends(get_neon_session),
):
    wf = await _get_or_404(neon, workflow_id)
    await library_service.delete_workflow(neon, wf)


# ── Import ────────────────────────────────────────────────────────────────

@router.post("/{workflow_id}/import", status_code=status.HTTP_201_CREATED)
async def import_workflow(
    workflow_id: str,
    data: WorkflowImport | None = None,
    neon: AsyncSession = Depends(get_neon_session),
    local: AsyncSession = Depends(get_session),
):
    """Clone a workflow's agents into the local canvas."""
    wf = await _get_or_404(neon, workflow_id)
    if data is None:
        data = WorkflowImport()
    agents = await library_service.import_workflow(neon, local, wf, data)
    return {"imported_agents": len(agents), "agent_ids": [a.id for a in agents]}
