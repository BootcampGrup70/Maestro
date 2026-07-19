"""Enumerations mirroring database.md.

SQLite has no native enum type, so these values are enforced with CHECK constraints on
the corresponding columns (declared on each model) and typed here for the app layer.
"""

from __future__ import annotations

from enum import Enum

import sqlalchemy as sa


class AgentStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    ERROR = "error"
    DONE = "done"
    QUEUED = "queued"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ToolOperation(str, Enum):
    READ = "read"
    WRITE = "write"


class ToolCallStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


def enum_type(enum_cls: type[Enum], name: str) -> sa.Enum:
    """Build a non-native SQLAlchemy Enum stored as TEXT with a named CHECK constraint.

    SQLite has no native enum, and SQLAlchemy's default Enum stores member *names*
    (e.g. ``IDLE``). We force ``values_callable`` so the lowercase *values* from
    database.md (e.g. ``idle``) are persisted, and ``name`` names the CHECK constraint.
    """
    return sa.Enum(
        enum_cls,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [m.value for m in members],
        name=name,
    )
