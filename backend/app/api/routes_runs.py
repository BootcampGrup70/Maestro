"""Start and list runs for an agent."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.run import RunCreate, RunRead
from app.services import agent_service, run_service

router = APIRouter(prefix="/agents/{agent_id}/runs", tags=["runs"])


@router.get("", response_model=list[RunRead])
async def list_runs(agent_id: str, session: AsyncSession = Depends(get_session)) -> list:
    if await agent_service.get_agent(session, agent_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return await run_service.list_runs(session, agent_id)


@router.post("", response_model=RunRead, status_code=status.HTTP_202_ACCEPTED)
async def start_run(
    agent_id: str, data: RunCreate, session: AsyncSession = Depends(get_session)
) -> object:
    agent = await agent_service.get_agent(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return await run_service.create_run(session, agent, data.prompt)
