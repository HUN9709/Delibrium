# Delibrium Panelist Server

Inheritance-based, multi-provider chat server. One codebase runs as a GPT,
Claude, or Gemini panelist purely through environment variables.

This directory implements **Milestone 1** of `PANELIST_SERVER.md`:

- Abstract `Panelist` base class owning the common chat + streaming lifecycle
- `FakePanelist` (provider-independent) for the skeleton and tests
- `ConversationStore` abstraction + async SQLite implementation
- Common Pydantic contracts (chat / conversation / provider / events)
- `/health`, `/v1/chat` (+ SSE streaming), `/v1/conversations*`, `/v1/models/current`
- Unit + API tests

Not yet implemented (later milestones): OpenAI / Anthropic / Gemini adapters,
tool calling, Mem0, MCP, Moderator, Reporter.

## Layout

```
app/
├─ main.py              FastAPI app + lifespan wiring
├─ config.py            Env-driven settings
├─ dependencies.py      FastAPI providers for settings/store/panelist
├─ api/                 chat, conversations, health, models routers
├─ panelists/           base.Panelist, fake.FakePanelist, factory
├─ runtime/             error model, SSE formatting
├─ schemas/             chat, conversation, provider, events contracts
├─ storage/             ConversationStore + async SQLite store
└─ observability/       logging
tests/                  base panelist, factory, chat API, streaming
```

## Setup (requires Python 3.11+)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Run

```powershell
# Defaults to the FakePanelist (see .env.example)
uvicorn app.main:app --reload --port 8000
```

```powershell
# Non-streaming
curl -X POST http://localhost:8000/v1/chat `
  -H "Content-Type: application/json" `
  -d '{"conversation_id":"c1","user_id":"u1","message":"hello"}'

# Streaming (SSE)
curl -N -X POST http://localhost:8000/v1/chat/stream `
  -H "Content-Type: application/json" `
  -d '{"conversation_id":"c1","user_id":"u1","message":"hello"}'
```

## Test

```powershell
pytest
```

## Running as different providers (later milestones)

The same image becomes a different panelist via env vars:

| Server | PANELIST_TYPE | PROVIDER | Port |
| ------ | ------------- | -------- | ---- |
| GPT    | `gpt`         | openai   | 8101 |
| Claude | `claude`      | anthropic| 8102 |
| Gemini | `gemini`      | google   | 8103 |

In Milestone 1 only `PANELIST_TYPE=fake` is functional; the others raise a
clear `NotImplementedError` at startup.
