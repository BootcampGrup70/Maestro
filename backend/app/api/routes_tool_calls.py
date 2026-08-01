"""Read a single agent's tool-call history."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db import get_session
from app.models.tool_call import ToolCall
from app.schemas.tool_call import ToolCallRead
from app.services import agent_service

router = APIRouter(prefix="/agents/{agent_id}/tool-calls", tags=["tool-calls"])


@router.get("", response_model=list[ToolCallRead])
async def list_tool_calls(
    agent_id: str, session: AsyncSession = Depends(get_session)
) -> list:
    if await agent_service.get_agent(session, agent_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    result = await session.execute(
        select(ToolCall).where(ToolCall.agent_id == agent_id).order_by(ToolCall.created_at)
    )
    return list(result.scalars().all())
