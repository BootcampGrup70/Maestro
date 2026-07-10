"""SQLModel table models mirroring database.md.

Importing this package registers every table on ``SQLModel.metadata`` (used by both
``create_all`` and Alembic autogenerate).
"""

from app.models.agent import Agent
from app.models.enums import (
    AgentStatus,
    MessageRole,
    RunStatus,
    ToolCallStatus,
    ToolOperation,
)
from app.models.message import Message
from app.models.meta import Meta
from app.models.run import Run
from app.models.tool_call import ToolCall

__all__ = [
    "Agent",
    "Message",
    "ToolCall",
    "Run",
    "Meta",
    "AgentStatus",
    "MessageRole",
    "ToolOperation",
    "ToolCallStatus",
    "RunStatus",
]
