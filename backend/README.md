# Maestro Backend

Async FastAPI service that drives Maestro's multi-agent canvas: it manages agents
(canvas nodes), runs prompts against local **Ollama** models, streams tokens and
reasoning to the frontend over a **WebSocket**, and persists everything to **SQLite**.

## Stack

- **FastAPI** + async, WebSocket for live updates
- **SQLModel** models + **Alembic** migrations, async engine via **aiosqlite**
- Official **`ollama`** async client
- Managed with **`uv`**

## Layout

```
app/
  main.py         # app factory + lifespan (startup normalization)
  config.py       # settings (env-driven)
  db.py           # async engine + session dependency
  models/         # SQLModel tables (mirror ../database.md)
  schemas/        # request/response DTOs + WebSocket event envelope
  api/            # HTTP routers (health, agents, messages, runs)
  ws/             # ConnectionManager + /ws endpoint + event builders
  services/       # agent_service, run_service, ollama_client, tools/
  core/           # ids, time, concurrency, startup normalization
alembic/          # migration environment + versions
tests/            # smoke tests
```

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

## Feature:  Advanced Agent Deletion & Canvas Sync

`DELETE /agents/{id}` now does three things beyond a bare row delete:

- **Cascading cleanup** - deleting an agent removes its `messages`, `runs`, and
  `tool_calls` rows too. This is enforced at the SQLite level (`ondelete="CASCADE"` on
  each `agent_id` foreign key, combined with the `PRAGMA foreign_keys = ON` set on every
  connection in `app/db.py`), not by application code.
- **Active-run guard** - if the agent has a `queued` or `running` row in `runs`, the
  delete is rejected with `409 Conflict` instead of tearing down state out from under a
  live background task. There's no run-cancellation path yet (see `TODO.md`), so refusing
  is the safe default; once task cancellation exists this can become stop-then-delete.
- **Live canvas sync** - on a successful delete, the server broadcasts an `agent_deleted`
  WebSocket event (`{"type": "agent_deleted", "agent_id": ...}`) so connected clients can
  remove the node without a manual refresh.

Implementation: `app/services/agent_service.py` (`AgentHasActiveRunError` + the guard in
`delete_agent`), `app/api/routes_agents.py` (409 mapping + broadcast), `app/schemas/ws.py`
+ `app/ws/events.py` (the new `AGENT_DELETED` event type/builder). Covered by
`tests/test_agent_deletion.py`.
