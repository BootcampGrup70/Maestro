"""FastAPI application factory + lifespan.

On startup we (optionally) create tables and always normalize stale runtime state so the
live node indicators match reality after a restart (see database.md).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_agents, routes_health, routes_messages, routes_runs
from app.config import get_settings
from app.core.startup import normalize_stale_state
from app.db import SessionLocal, create_db_and_tables
from app.ws import routes_ws

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.auto_create_tables:
        await create_db_and_tables()
    async with SessionLocal() as session:
        await normalize_stale_state(session)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Maestro Backend", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_health.router, prefix="/api")
    app.include_router(routes_agents.router, prefix="/api")
    app.include_router(routes_messages.router, prefix="/api")
    app.include_router(routes_runs.router, prefix="/api")
    app.include_router(routes_ws.router)  # /ws (no /api prefix)

    return app


app = create_app()
