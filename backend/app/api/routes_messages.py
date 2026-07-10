"""Read a single agent's conversation history."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db import get_session
from app.models.message import Message
from app.schemas.message import MessageRead
from app.services import agent_service

router = APIRouter(prefix="/agents/{agent_id}/messages", tags=["messages"])


@router.get("", response_model=list[MessageRead])
async def list_messages(
    agent_id: str, session: AsyncSession = Depends(get_session)
) -> list:
    if await agent_service.get_agent(session, agent_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    result = await session.execute(
        select(Message).where(Message.agent_id == agent_id).order_by(Message.seq)
    )
    return list(result.scalars().all())
