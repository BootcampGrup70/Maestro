"""Neon (online PostgreSQL) connection for the shared library.

This module provides a separate async engine and session factory that connects
to the Neon cloud database. Only the library tables live here — all local
agent/run/message data stays in the local SQLite database.

Connection string is read from the MAESTRO_NEON_DATABASE_URL env variable.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import HTTPException, status
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

from app.config import get_settings
from app.models.library_agent import LibraryAgent
from app.models.library_workflow import LibraryWorkflow

library_metadata = SQLModel.metadata  # both models register here


def _build_engine() -> AsyncEngine | None:
    """Build the Neon engine, or return None if unconfigured.

    The library feature is optional: most local dev setups won't have a Neon
    credential, and the rest of the app (agents/runs/messages) must keep
    working without one.
    """
    settings = get_settings()
    if not settings.neon_database_url:
        return None

    # asyncpg driver: swap "postgresql://" → "postgresql+asyncpg://"
    neon_url = make_url(
        settings.neon_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    )

    # asyncpg's connect() doesn't understand libpq's "sslmode" query param (used by
    # psycopg2-style URLs, e.g. Neon's default connection string). Strip it and
    # pass the equivalent as a connect_arg instead.
    query = dict(neon_url.query)
    sslmode = query.pop("sslmode", None)
    neon_url = neon_url.set(query=query)

    connect_args: dict = {"ssl": "require"} if sslmode in ("require", "verify-ca", "verify-full") else {}

    # Neon's "-pooler" endpoint routes through PgBouncer in transaction-pooling
    # mode, which is incompatible with asyncpg's server-side prepared statement
    # cache (connections/statements can be reused across unrelated transactions,
    # so cached plans go stale — e.g. "cached statement plan is invalid due to a
    # database schema or configuration change"). Disable it.
    if "-pooler" in neon_url.host:
        connect_args["statement_cache_size"] = 0

    return create_async_engine(
        neon_url,
        echo=False,
        future=True,
        pool_pre_ping=True,          # handle Neon scale-to-zero wakeups
        pool_size=5,
        max_overflow=5,
        connect_args=connect_args,
    )


neon_engine: AsyncEngine | None = _build_engine()

NeonSessionLocal = (
    async_sessionmaker(neon_engine, class_=AsyncSession, expire_on_commit=False)
    if neon_engine is not None
    else None
)


async def create_neon_tables() -> None:
    """Create library tables on Neon (idempotent). No-op if unconfigured."""
    if neon_engine is None:
        return
    async with neon_engine.begin() as conn:
        await conn.run_sync(
            SQLModel.metadata.create_all,
            tables=[
                LibraryWorkflow.__table__,
                LibraryAgent.__table__,
            ],
        )


async def get_neon_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an async Neon session."""
    if NeonSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Shared workflow library is not configured (set MAESTRO_NEON_DATABASE_URL).",
        )
    async with NeonSessionLocal() as session:
        yield session
