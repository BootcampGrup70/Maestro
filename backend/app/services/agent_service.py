"""Agent CRUD logic (fully implemented for the vertical slice)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.time import now_ms
from app.models.agent import Agent
from app.models.enums import AgentStatus
from app.schemas.agent import AgentCreate, AgentUpdate
from app.services import ollama_client

async def create_agent(session: AsyncSession, data: AgentCreate) -> Agent:
    available_models = await ollama_client.list_models()
    if data.model not in available_models:
        raise ValueError(f"Model '{data.model}' is not available in Ollama.")

    agent = Agent(
        name=data.name,
        model=data.model,
        system_prompt=data.system_prompt,
        settings=data.settings,
        parent_id=data.parent_id,
        canvas_x=data.canvas_x,
        canvas_y=data.canvas_y,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


async def get_agent(session: AsyncSession, agent_id: str) -> Agent | None:
    return await session.get(Agent, agent_id)


async def list_agents(session: AsyncSession) -> list[Agent]:
    result = await session.execute(select(Agent).order_by(Agent.created_at))
    return list(result.scalars().all())


async def update_agent(session: AsyncSession, agent: Agent, data: AgentUpdate) -> Agent:
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(agent, key, value)
    agent.updated_at = now_ms()
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


async def update_position(
    session: AsyncSession, agent: Agent, canvas_x: float, canvas_y: float
) -> Agent:
    agent.canvas_x = canvas_x
    agent.canvas_y = canvas_y
    agent.updated_at = now_ms()
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


async def set_status(
    session: AsyncSession,
    agent: Agent,
    status: AgentStatus,
    error_message: str | None = None,
) -> Agent:
    agent.status = status
    agent.error_message = error_message
    agent.updated_at = now_ms()
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


async def delete_agent(session: AsyncSession, agent: Agent) -> None:
    await session.delete(agent)
    await session.commit()
