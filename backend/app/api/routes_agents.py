"""Agent CRUD + canvas position endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.enums import AgentStatus
from app.schemas.agent import AgentCreate, AgentPositionUpdate, AgentRead, AgentUpdate
from app.schemas.run import RunRead
from app.services import agent_service, run_service
from app.ws import events
from app.ws.manager import get_manager

router = APIRouter(prefix="/agents", tags=["agents"])


async def _get_or_404(session: AsyncSession, agent_id: str):
    agent = await agent_service.get_agent(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.get("", response_model=list[AgentRead])
async def list_agents(session: AsyncSession = Depends(get_session)) -> list:
    return await agent_service.list_agents(session)


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: AgentCreate, session: AsyncSession = Depends(get_session)
) -> object:
    agent = await agent_service.create_agent(session, data)
    await get_manager().broadcast(events.agent_status(agent.id, AgentStatus(agent.status)))
    return agent


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(agent_id: str, session: AsyncSession = Depends(get_session)) -> object:
    return await _get_or_404(session, agent_id)


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: str, data: AgentUpdate, session: AsyncSession = Depends(get_session)
) -> object:
    agent = await _get_or_404(session, agent_id)
    return await agent_service.update_agent(session, agent, data)


@router.patch("/{agent_id}/position", response_model=AgentRead)
async def update_position(
    agent_id: str, data: AgentPositionUpdate, session: AsyncSession = Depends(get_session)
) -> object:
    agent = await _get_or_404(session, agent_id)
    return await agent_service.update_position(session, agent, data.canvas_x, data.canvas_y)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str, session: AsyncSession = Depends(get_session)) -> None:
    agent = await _get_or_404(session, agent_id)
    await agent_service.delete_agent(session, agent)


@router.post("/{agent_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_run(
    agent_id: str, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    await _get_or_404(session, agent_id)
    if not run_service.cancel_run(agent_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Agent has no active run to cancel"
        )
    return {"status": "cancelling"}


@router.post("/{agent_id}/restart", response_model=RunRead, status_code=status.HTTP_202_ACCEPTED)
async def restart_run(
    agent_id: str, session: AsyncSession = Depends(get_session)
) -> object:
    agent = await _get_or_404(session, agent_id)
    try:
        return await run_service.restart_run(session, agent)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/{agent_id}/restart-tree",
    response_model=list[RunRead],
    status_code=status.HTTP_202_ACCEPTED,
)
async def restart_tree(
    agent_id: str, session: AsyncSession = Depends(get_session)
) -> object:
    agent = await _get_or_404(session, agent_id)
    try:
        return await run_service.restart_tree(session, agent)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
