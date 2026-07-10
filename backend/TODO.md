# TODO

---

## Done (skeleton baseline)

- [x] Project scaffolding: `uv`, `pyproject.toml`, `.env.example`, `.gitignore`, README
- [x] Async DB layer (`app/db.py`): engine, session dependency, `PRAGMA foreign_keys=ON`
- [x] SQLModel tables mirroring `database.md` (`app/models/`) with CHECK constraints + indexes
- [x] Alembic wired (async `env.py`) + initial migration; `create_all()` dev fallback
- [x] Startup normalization of stale runtime state (`app/core/startup.py`)
- [x] Agent CRUD API + canvas position (`app/api/routes_agents.py`)
- [x] Message history read + run start/list APIs
- [x] WebSocket endpoint, `ConnectionManager` broadcast, event envelope + builders
- [x] Ollama async streaming client wrapper (`app/services/ollama_client.py`)
- [x] Run orchestration vertical slice: queue -> semaphore -> stream -> persist -> done/idle
- [x] Smoke tests (health + agent CRUD)

---

## 1. Tool-calling (highest priority - main open stub)

- [ ] Implement `run_service._handle_tool_calls` (`app/services/run_service.py`) `(stub)`
  - [ ] Flip agent status to `tool_calling` + broadcast `agent_status`
  - [ ] Insert a `tool_calls` row per call (status `pending`) + broadcast `tool_call_created`
  - [ ] Dispatch via `services/tools/registry.dispatch` (filesystem read/write)
  - [ ] Update the row (`success`/`error`, result/error_message) + broadcast `tool_call_updated`
  - [ ] Append a `tool`-role message with the result and re-invoke the model in a loop
    ```
    until no more tool calls are returned
    ```
- [ ] Confirm the sandbox in `services/tools/filesystem.py` rejects path escapes (tests below)
- [ ] Decide max tool-call iterations per run (guard against infinite loops)

## 2. Runs & concurrency

- [ ] Verify `Semaphore(2)` behavior with 3+ concurrent runs (extra runs stay `queued`)
- [ ] Cancel/stop a running run (needed for crash-restart of a parent + its subagents)
- [ ] Restart action: re-queue a run for an agent left in `error`
- [ ] Parent crash -> stop subagents and restart together in one action (README requirement)
- [ ] Track the running `asyncio.Task` per agent so it can be cancelled

## 3. WebSocket / live updates

- [ ] Handle inbound client messages in `app/ws/routes_ws.py` `(stub)`:
  ```
  user interjecting a new instruction into a running agent
  ```
- [ ] Define the inbound message contract (schema in `app/schemas/ws.py`)
- [ ] Send a snapshot of current agent states on new connection (initial sync)
- [ ] Decide on reconnect/backfill strategy (missed events while disconnected)

## 4. Agents & canvas

- [ ] Validate the selected `model` exists in Ollama on create (list local models)
- [ ] Endpoint to list available Ollama models (for the "+" create dialog)
- [ ] Validate `parent_id` references an existing agent
- [ ] Agent deletion (backend `DELETE /agents/{id}` exists in skeleton; finish the rest)
  - [ ] Confirm cascades: `messages`/`tool_calls`/`runs` deleted, children detached
    ```
    (`parent_id` -> NULL) per `database.md`
    ```
  - [ ] Block or safely handle deleting an agent with an active run (stop/cancel first)
  - [ ] Broadcast an `agent_deleted` WS event so the canvas removes the node live
    ```
    (add the type to `app/schemas/ws.py` + a builder in `app/ws/events.py`)
    ```
  - [ ] Frontend: delete action on the node (with confirm) + remove connected edges
- [ ] Editable agent settings from the frontend (basic model params: `max_tokens`/`num_predict`,
  ```
  `temperature`, `num_ctx`, `system_prompt`)
  ```
  - Backend already supports this: `PATCH /agents/{id}` (`AgentUpdate.settings` in
  `app/schemas/agent.py`) persists to the `agents.settings` JSON column - so we DO record them.
  - [ ] Agree on the canonical settings keys and map them to Ollama's `options`
    (note `max_tokens` -> Ollama `num_predict`) in `run_service` / `ollama_client`
  - [ ] Validate incoming settings (types/ranges) before saving; ignore unknown keys
  - [ ] Frontend: settings form in the agent panel that PATCHes on save

## 5. Persistence & lifecycle

- [ ] Confirm restart behavior matches `database.md` (persistent) - align with README wording
- [ ] Decide `meta` table usage (schema version flag, app-level flags)
- [ ] Migration workflow doc for the team (when/how to autogenerate + review)

## 6. Testing

- [ ] Unit tests for filesystem sandbox (path escape rejection, read/write happy path)
- [ ] Test run lifecycle with a mocked `ollama_client.stream_chat` (no live Ollama)
- [ ] Test startup normalization resets stale `thinking`/`queued`/`running` rows
- [ ] WebSocket test: connect, trigger a run, assert event sequence
- [ ] CI: run `uv run pytest` on push

## 7. Ops & DX

- [ ] Structured logging (per-agent / per-run context)
- [ ] Basic error-to-HTTP mapping (consistent error response shape)
- [ ] Lint/format config (ruff) + pre-commit
- [ ] Health check that also reports Ollama reachability

---

## Explicitly out of scope for v1 (see README backlog)

Auto subagent creation, multi-tool registry, MCP, effort levels, token tracking, model
comparison, pause/resume, shareable configs, auth. Leave `TODO(v2)` markers if you touch
related code.