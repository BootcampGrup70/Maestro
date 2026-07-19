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


## Feature: run orchestration & crash handling

Implements TODO.md section 2 ("Runs & concurrency"): cancelling a run, restarting an
agent left in `error`, and cascading a parent's crash to its subagents.

### New endpoints

- `POST /agents/{id}/cancel` -- cancel the agent's in-flight run (queued or running).
  409 if the agent has no active run.
- `POST /agents/{id}/restart` -- retry an agent left in `error`, reusing its last
  prompt without adding a duplicate user message. 409 if the agent isn't in `error`.
- `POST /agents/{id}/restart-tree` -- restart an agent *and* every descendant of it
  currently in `error`, together, in one action. 409 if nothing in the tree is erroring.

### How it works

- `app/core/tasks.py` is a new process-wide `agent_id -> asyncio.Task` registry. Runs
  are fired via `asyncio.create_task` in `run_service._queue_run`; without this
  registry there was no way to look a task back up later in order to cancel it.
- Cancelling calls `task.cancel()`, which raises `asyncio.CancelledError` inside
  `_execute_run`. Both a still-queued run (waiting on the concurrency semaphore) and a
  mid-stream run are handled correctly -- the run lands on the new `cancelled` status
  and the agent goes back to `idle`.
- When a run's model call raises (a "crash"), the agent goes to `error` as before, and
  `run_service._cascade_stop_children` now also walks
  `agent_service.list_descendants` (the *whole* subtree reachable via `parent_id`, not
  just direct children) and cancels each descendant's in-flight run. Descendants are
  re-stamped `error` (rather than left at `idle`) specifically so `restart-tree` can
  find and retry them alongside the parent.

### Database changes

- `RunStatus` gained a `cancelled` member (`app/models/enums.py`), kept distinct from
  `error` so a user-initiated stop and a genuine failure aren't conflated in run
  history or in cascade/restart decisions.
- New migration: `alembic/versions/ecf722526565_add_cancelled_run_status.py` -- widens
  the `ck_runs_status` CHECK constraint via SQLite batch mode (upgrade/downgrade both
  verified to round-trip cleanly). Run `uv run alembic upgrade head` to apply it to an
  existing `maestro.db`. If your local `maestro.db` predates Alembic entirely (created
  via the `create_all()` dev fallback, no `alembic_version` table), adopt it first:
  `uv run alembic stamp 9063f7b89c8d` (the initial schema, which matches what
  `create_all()` produces) and then `uv run alembic upgrade head`.
- `db_statements.sql` regenerated to match the current schema.

### Tests

- `tests/test_run_concurrency.py` -- confirms `Semaphore(2)` actually queues a 3rd
  concurrent run instead of letting it through.
- `tests/test_run_cancel.py` -- cancelling frees the semaphore slot for a run that was
  queued behind it; 409/404 edge cases.
- `tests/test_run_restart.py` -- restart retries the model call without duplicating
  the user message in history.
- `tests/test_run_cascade.py` -- descendant lookup (including grandchildren), a full
  parent-crash -> children-stopped -> `restart-tree`-recovers-everything scenario, and
  409/404 edge cases.
- `tests/helpers.py` / `tests/conftest.py` -- shared async test helpers, an
  `async_client` fixture (needed so a test can interleave `await` with the background
  run tasks on the same event loop, unlike the sync `TestClient`), and an autouse
  cleanup fixture that drains any task a test leaves in flight so it can't leak into
  the next test's (process-wide, cached) semaphore/task-registry state.