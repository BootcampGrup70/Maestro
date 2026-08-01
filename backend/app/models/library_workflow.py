"""``library_workflows`` table (Neon) — shared workflow packages.

Each row represents a published multi-agent workflow that any user can
browse and import into their local canvas.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, Text
from sqlmodel import JSON, Field, SQLModel

from app.core.ids import new_id
from app.core.time import now_ms


class LibraryWorkflow(SQLModel, table=True):
    __tablename__ = "library_workflows"

    id: str = Field(default_factory=new_id, primary_key=True)

    name: str
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))

    agent_count: int = Field(default=0)
    import_count: int = Field(default=0)

    # now_ms() returns a 13-digit epoch-millisecond value, which overflows a
    # 32-bit Postgres INTEGER (the SQLModel default for `int`).
    created_at: int = Field(default_factory=now_ms, sa_column=Column(BigInteger, nullable=False))
    updated_at: int = Field(default_factory=now_ms, sa_column=Column(BigInteger, nullable=False))
