"""``meta`` table - simple key/value app metadata (SYSTEM group)."""

from __future__ import annotations

from sqlmodel import Field, SQLModel


class Meta(SQLModel, table=True):
    __tablename__ = "meta"

    key: str = Field(primary_key=True)
    value: str | None = Field(default=None)
