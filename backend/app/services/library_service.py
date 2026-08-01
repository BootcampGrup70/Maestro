"""Library service — publish, browse, import, and manage shared workflows.

Publishing snapshots agent configurations into Neon. Importing clones them
back into the user's local SQLite as real agents with regenerated IDs and
restored parent-child relationships.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.ids import new_id
from app.core.time import now_ms
from app.models.agent import Agent
from app.models.enums import AgentStatus
from app.models.library_agent import LibraryAgent
from app.models.library_workflow import LibraryWorkflow
from app.schemas.library import (
    LibraryAgentData,
    WorkflowImport,
    WorkflowPublish,
    WorkflowUpdate,
)


# ── Publish ───────────────────────────────────────────────────────────────

async def publish(
    neon: AsyncSession,
    local: AsyncSession,
    data: WorkflowPublish,
) -> LibraryWorkflow:
    """Publish a workflow to the shared library.

    If ``agent_ids`` is provided, those agents are read from the local DB and
    their configs are snapshotted. Otherwise ``agents`` (explicit list) is used.
    """

    agent_data_list: list[LibraryAgentData] = []

    if data.agent_ids:
        # Snapshot from local canvas
        ref_map: dict[str, str] = {}  # local agent id → local_ref letter
        agents: list[Agent] = []

        for agent_id in data.agent_ids:
            agent = await local.get(Agent, agent_id)
            if agent is None:
                raise ValueError(f"Agent '{agent_id}' not found in local DB.")
            agents.append(agent)
            ref_map[agent.id] = chr(65 + len(ref_map))  # A, B, C, ...

        for agent in agents:
            parent_ref = ref_map.get(agent.parent_id) if agent.parent_id else None
            agent_data_list.append(
                LibraryAgentData(
                    name=agent.name,
                    model=agent.model,
                    system_prompt=agent.system_prompt,
                    settings=agent.settings,
                    canvas_x=agent.canvas_x,
                    canvas_y=agent.canvas_y,
                    local_ref=ref_map[agent.id],
                    parent_local_ref=parent_ref,
                )
            )
    else:
        agent_data_list = data.agents

    if not agent_data_list:
        raise ValueError("At least one agent is required to publish a workflow.")

    # Create workflow
    workflow = LibraryWorkflow(
        name=data.name,
        description=data.description,
        tags=data.tags,
        agent_count=len(agent_data_list),
    )
    neon.add(workflow)
    await neon.flush()  # get workflow.id

    # Create library agents
    for ad in agent_data_list:
        la = LibraryAgent(
            workflow_id=workflow.id,
            name=ad.name,
            model=ad.model,
            system_prompt=ad.system_prompt,
            settings=ad.settings,
            canvas_x=ad.canvas_x,
            canvas_y=ad.canvas_y,
            local_ref=ad.local_ref,
            parent_local_ref=ad.parent_local_ref,
        )
        neon.add(la)

    await neon.commit()
    await neon.refresh(workflow)
    return workflow


# ── Browse / Search ───────────────────────────────────────────────────────

async def list_workflows(
    neon: AsyncSession,
    *,
    tag: str | None = None,
    search: str | None = None,
) -> list[LibraryWorkflow]:
    stmt = select(LibraryWorkflow).order_by(LibraryWorkflow.created_at.desc())
    result = await neon.execute(stmt)
    items = list(result.scalars().all())

    if tag:
        items = [w for w in items if tag.lower() in [t.lower() for t in w.tags]]
    if search:
        q = search.lower()
        items = [
            w for w in items
            if q in w.name.lower() or (w.description and q in w.description.lower())
        ]
    return items


async def get_workflow(neon: AsyncSession, workflow_id: str) -> LibraryWorkflow | None:
    return await neon.get(LibraryWorkflow, workflow_id)


async def get_workflow_agents(
    neon: AsyncSession, workflow_id: str
) -> list[LibraryAgent]:
    stmt = select(LibraryAgent).where(LibraryAgent.workflow_id == workflow_id)
    result = await neon.execute(stmt)
    return list(result.scalars().all())


# ── Update ────────────────────────────────────────────────────────────────

async def update_workflow(
    neon: AsyncSession, workflow: LibraryWorkflow, data: WorkflowUpdate
) -> LibraryWorkflow:
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(workflow, key, value)
    workflow.updated_at = now_ms()
    neon.add(workflow)
    await neon.commit()
    await neon.refresh(workflow)
    return workflow


# ── Delete ────────────────────────────────────────────────────────────────

async def delete_workflow(neon: AsyncSession, workflow: LibraryWorkflow) -> None:
    # Delete agents first
    agents = await get_workflow_agents(neon, workflow.id)
    for agent in agents:
        await neon.delete(agent)
    await neon.delete(workflow)
    await neon.commit()


# ── Import ────────────────────────────────────────────────────────────────

async def import_workflow(
    neon: AsyncSession,
    local: AsyncSession,
    workflow: LibraryWorkflow,
    data: WorkflowImport,
) -> list[Agent]:
    """Clone a workflow's agents into the local canvas.

    Regenerates all IDs and reconstructs parent-child relationships using
    the local_ref / parent_local_ref mapping.
    """

    lib_agents = await get_workflow_agents(neon, workflow.id)

    # Phase 1: create agents, track ref → new_id mapping
    ref_to_new_id: dict[str, str] = {}
    new_agents: list[Agent] = []

    for la in lib_agents:
        new_agent_id = new_id()
        ref_to_new_id[la.local_ref] = new_agent_id

        agent = Agent(
            id=new_agent_id,
            name=la.name,
            model=la.model,
            system_prompt=la.system_prompt,
            settings=la.settings,
            status=AgentStatus.IDLE,
            canvas_x=la.canvas_x + data.offset_x,
            canvas_y=la.canvas_y + data.offset_y,
        )
        new_agents.append(agent)
        local.add(agent)

    # Phase 2: set parent_id from the mapping
    for la, agent in zip(lib_agents, new_agents):
        if la.parent_local_ref and la.parent_local_ref in ref_to_new_id:
            agent.parent_id = ref_to_new_id[la.parent_local_ref]

    await local.commit()

    # Increment import count on Neon
    workflow.import_count += 1
    workflow.updated_at = now_ms()
    neon.add(workflow)
    await neon.commit()

    # Refresh local agents
    for agent in new_agents:
        await local.refresh(agent)

    return new_agents
