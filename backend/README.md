# Maestro Backend

Async FastAPI service that drives Maestro's multi-agent canvas: it manages agents
(canvas nodes), runs prompts against local **Ollama** models, streams tokens and
reasoning to the frontend over a **WebSocket**, and persists everything to **SQLite**.

## Stack

- **FastAPI** + async, WebSocket for live updates
- **SQLModel** models + **Alembic** migrations, async engine via **aiosqlite**
- Official **`ollama`** async client
- Optional **Neon (cloud Postgres)** connection for the shared workflow library
- Managed with **`uv`**

## Layout

```
app/
  main.py         # app factory + lifespan (startup normalization)
  config.py       # settings (env-driven)
  db.py           # async engine + session dependency (local SQLite)
  neon_db.py      # async engine + session dependency (Neon, optional — library feature)
  models/         # SQLModel tables (mirror ../database.md), incl. library_workflow/library_agent
  schemas/        # request/response DTOs + WebSocket event envelope
  api/            # HTTP routers (health, agents, messages, runs, tool_calls, library)
  ws/             # ConnectionManager + /ws endpoint + event builders
  services/       # agent_service, run_service, ollama_client, tools/, library_service
  core/           # ids, time, concurrency, startup normalization
alembic/          # migration environment + versions
tests/            # smoke tests
```

### Shared workflow library

`GET/POST /api/library`, `GET/PATCH/DELETE /api/library/{id}`, and
`POST /api/library/{id}/import` let a user publish a snapshot of local agents
(as a named, taggable "workflow") to a shared **Neon Postgres** database, browse
what others have published, and import a workflow back as new local agents
(IDs regenerated, parent/child structure preserved). Local agent/run/message
data always stays in SQLite — Neon only stores published workflow snapshots.

This feature is optional: without `MAESTRO_NEON_DATABASE_URL` set (see
`.env.example`), the rest of the app runs normally and `/api/library/*`
endpoints return `503`.

## Setup

With `uv` (preferred):

```bash
cd backend
uv sync --extra dev          # create .venv and install deps
cp .env.example .env         # optional; defaults work out of the box
```

With plain `pip`:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # .venv\Scripts\activate on Windows
pip install -e ".[dev]"
cp .env.example .env         # optional; defaults work out of the box
```

## Run

```bash
uv run uvicorn app.main:app --reload
# or, with pip (venv activated):
uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health
- WebSocket: ws://localhost:8000/ws

You need a running Ollama instance (`ollama serve`) with at least one model pulled
(e.g. `ollama pull llama3`) for agent runs to actually stream output.

## Database & migrations

The database schema is defined in [`../database.md`](../database.md) and implemented as
SQLModel tables under `app/models/`.

```bash
# Apply migrations (creates maestro.db):
uv run alembic upgrade head        # or: alembic upgrade head (pip + activated venv)

# After changing a model, autogenerate a new migration:
uv run alembic revision --autogenerate -m "describe change"   # or: alembic revision --autogenerate -m "..."
```

In development you can skip Alembic: the app calls `create_all()` on startup when
`MAESTRO_AUTO_CREATE_TABLES=1` (default), so it boots against a fresh DB.

## Tests

```bash
uv run pytest
# or, with pip (venv activated):
pytest
```

## Working on the skeleton

One vertical slice is fully implemented as a reference: **create agent -> start run ->
stream from Ollama -> broadcast over WebSocket -> persist messages**. Other areas are
stubbed with typed signatures and `TODO`s so the team can build in parallel. The main
open stub is real tool-calling in `app/services/run_service.py` and
`app/services/tools/filesystem.py`.
