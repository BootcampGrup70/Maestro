# Verifying the backend baseline

This walks through everything needed to confirm the "skeleton baseline" in `TODO.md` is
actually working: agent CRUD, run orchestration, live Ollama streaming, WebSocket
broadcast, and message persistence. Steps 1-2 are automated; steps 3+ are manual since
there's no test yet covering the run/streaming/WebSocket path.

## 1. Install deps

```bash
cd backend
uv sync --extra dev
```

## 2. Run the automated smoke tests

```bash
uv run pytest -v
```

Expect `6 passed`. These only cover the health endpoint + agent CRUD (create/get/list/
update position/delete/404) — they do **not** exercise runs, Ollama streaming, or the
WebSocket.

## 3. Pull the model

We're using `qwen3.5:4b` for now (model choice will become selectable per-agent later).

```bash
ollama serve        # skip if the Ollama app/daemon is already running
ollama pull qwen3.5:4b
ollama list          # confirm qwen3.5:4b shows up
```

## 4. Start the backend

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Confirm it's up:

```bash
curl -s http://localhost:8000/api/health
```

Expect `{"status":"ok","version":"..."}`.

## 5. Create an agent

```bash
curl -s -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "model": "qwen3.5:4b"}' | python3 -m json.tool
```

Copy the `"id"` from the response into a variable (same terminal session only — re-set
it if you open a new tab):

```bash
AGENT_ID=paste-the-id-here
```

## 6. Open a WebSocket listener *before* starting a run

Install once: `brew install websocat` (or use the browser DevTools alternative below).

```bash
websocat ws://localhost:8000/ws
```

Leave this running in its own terminal — every event gets printed as JSON.

Browser alternative (no install): open DevTools console anywhere and paste:

```js
const ws = new WebSocket("ws://localhost:8000/ws");
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

## 7. Start a run

```bash
curl -s -X POST http://localhost:8000/api/agents/$AGENT_ID/runs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "say hello"}' | python3 -m json.tool
```

Expect a `"status": "queued"` run object back immediately.

## 8. Watch the WebSocket terminal

Expected event order:

```
agent_status      (status: queued)
run_started
agent_status      (status: thinking)
message_delta     (repeated, one per streamed chunk)
message_created   (role: assistant)
run_finished      (status: done)
agent_status      (status: done)
```

If Ollama isn't reachable or the model name doesn't match, you should get an `error`
event and `agent_status` → `error` instead of a hang — worth testing that path too (stop
Ollama and repeat step 7).

## 9. Confirm persistence

```bash
curl -s http://localhost:8000/api/agents/$AGENT_ID | python3 -m json.tool
```

Expect `"status": "done"` (or `"error"` with `error_message` populated).

## What this does *not* cover

Per `TODO.md`, these are still stubs — don't treat their absence as a bug:

- Tool-calling (`run_service._handle_tool_calls` is a no-op logger)
- Cancel/stop a run, restart-after-error, parent/subagent crash cascade
- Inbound WebSocket messages (user interjecting mid-run)
- Model-exists validation on agent create, listing available Ollama models
- Cascading delete confirmation / `agent_deleted` WS broadcast
