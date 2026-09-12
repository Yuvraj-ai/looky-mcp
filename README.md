<!-- prettier-ignore -->
<div align="center">

<img src="./frontend/public/favicon.svg" alt="Vision MCP logo" align="center" height="64" />

# Vision MCP

Self-hosted vision for your coding agent

**Bring-your-own-model MCP server for image understanding** — connect any OpenAI-compatible vision LLM to OpenCode (or any MCP client) with per-user profiles, prompts, and keys.

[FastAPI](https://fastapi.tiangolo.com) • [Model Context Protocol](https://modelcontextprotocol.io) • [LangChain](https://python.langchain.com) • [React](https://react.dev) • [PostgreSQL](https://www.postgresql.org)

[Overview](#overview) • [Features](#features) • [Getting started](#getting-started) • [Using the app](#using-the-app) • [Connect an agent](#connect-an-agent) • [Deployment](#deployment) • [Project layout](#project-layout)

</div>

---

## Overview

Coding agents can't see. Vision MCP gives them eyes: an MCP server that exposes `describe_image` and `ocr_image` tools, backed by **your own vision model** (OpenAI, OpenRouter, a local vLLM endpoint — anything OpenAI-compatible).

You configure everything through a small web app: system prompts, vision model profiles (endpoint, model, API key — encrypted at rest), and a personal MCP key. The agent authenticates with that key, and every tool call routes through your **active profile** — you switch models without touching the agent's config.

```
                        ┌───────────────────┐
                        │      Browser       │
                        │  (Vite + React)    │
                        └─────────┬──────────┘
                                  │  REST (/api/...)
                                  ▼
┌───────────────────────────────────────────────────────────────┐
│                 Python backend (FastAPI, 1 process)          │
│                                                               │
│   /api/* (session auth)          /mcp (Bearer MCP key)        │
│          │                                │                   │
│          └────────► Shared service layer ◄─┘                  │
│                 (rate limits, validation, VisionService)      │
└────────────────────┬───────────────────────────┬───────────────┘
                     │                           │
              PostgreSQL                  LangChain ChatOpenAI
        (users, prompts,                        │
         profiles, MCP keys)                    ▼
                                  OpenAI-compatible Vision LLM
```

One process, one deployable unit: REST API and MCP endpoint share the database pool, rate limiter, and service layer. Built for small single-server deployments.

> [!NOTE]
> Accounts are **admin-provisioned only** — there is no public signup. Login is email/password or Google OAuth (if configured).

## Features

- **2 MCP tools** — `describe_image` (general visual understanding) and `ocr_image` (literal text extraction), Streamable HTTP transport
- **Bring your own model** — any OpenAI-compatible endpoint; multiple profiles, one active
- **Reusable system prompts** — plus universal extra instructions appended to every describe call
- **Keys never leak** — provider API keys encrypted at rest; MCP key shown once, stored hashed; OpenCode config references it via `{env:VISION_MCP_KEY}`
- **Guardrails** — image size/type validation, per-user rate limits, concurrency limits, DNS-rebinding protection
- **Zero-system-Postgres dev setup** — dev script bundles a Postgres via `pgserver`

## Getting started

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python 3.12+)
- [Node.js](https://nodejs.org) LTS + npm

### 1. Backend

From the repo root:

```bash
uv run python run_backend.py --migrate
```

This starts a bundled Postgres (data in `backend/.pgdata/`), applies migrations on first run, and serves the API + MCP server at `http://localhost:8000`. Drop `--migrate` for subsequent runs.

> [!TIP]
> To use an existing Postgres instead, configure `DATABASE_URL` in `backend/.env` and run `uvicorn app.main:app` from `backend/` (see `backend/.env.example` for all variables).

### 2. Frontend

```bash
cd frontend
npm install   # first time only
npm run dev
```

Web app at `http://localhost:5173`.

### 3. Create your login

```bash
cd backend
uv run python scripts/create_user.py --email you@example.com --password 'your-password'
```

## Using the app

1. **System Prompts** — write the persona your vision model uses (e.g. *"You are a UI reviewer"*), plus universal extra instructions applied to every describe call
2. **Vision Profiles** — bind endpoint + model + API key + system prompt; **activate** one profile — all MCP tool calls use it
3. **MCP Access** — generate your API key (shown once), revoke/rotate anytime

Full walkthrough: [`USER_MANUAL.md`](./USER_MANUAL.md).

## Connect an agent

The **MCP Access** page shows a ready-to-copy OpenCode config snippet:

```json
{
  "mcp": {
    "vision": {
      "type": "http",
      "url": "http://localhost:8000/mcp",
      "headers": { "Authorization": "Bearer {env:VISION_MCP_KEY}" }
    }
  }
}
```

Export the key (`export VISION_MCP_KEY=vmcp-...`), paste the snippet into `opencode.json`, restart the agent — it can now call `describe_image` and `ocr_image`.

## Development

```bash
# backend (from backend/)
uv run pytest                  # 106 tests + 1 opt-in e2e skip
uv run ruff check .            # lint
uv run black --check .         # format
uv run mypy app                # types

# frontend (from frontend/)
npm run build                  # tsc + vite
npm run lint
npm run typecheck
```

Real-provider e2e tests are opt-in: set `VISION_E2E_BASE_URL`, `VISION_E2E_API_KEY`, `VISION_E2E_MODEL` before running pytest.

## Deployment

Single uvicorn worker (deliberate — the in-memory rate/concurrency limiter requires it), behind Caddy or nginx for TLS + SPA hosting. Artifacts in [`deploy/`](./deploy/README.md): Dockerfile, docker-compose, Caddyfile, nginx.conf, systemd unit.

Quick start: `docker compose -f deploy/docker-compose.yml up -d` with a filled-in env file — details in [`deploy/README.md`](./deploy/README.md).

## Project layout

```
├── run_backend.py        # one-command dev launcher (repo root)
├── backend/
│   ├── app/
│   │   ├── api/         # REST routes (auth, prompts, profiles, MCP creds)
│   │   ├── auth/        # sessions, OAuth, MCP key auth middleware
│   │   ├── db/           # SQLAlchemy models + Alembic migrations
│   │   ├── mcp/           # MCP server: describe_image, ocr_image
│   │   ├── repositories/  # DB access layer
│   │   └── services/     # VisionService, rate/concurrency limits, validation
│   ├── scripts/          # dev.py, create_user.py
│   └── tests/            # pytest suite (incl. full-stack MCP e2e)
├── frontend/             # React SPA (Vite, TypeScript)
├── deploy/               # Docker/compose/Caddy/nginx/systemd
├── docs/                 # architecture & decision records
├── vision_mcp_architecture.md   # full architecture spec
└── USER_MANUAL.md         # end-user guide
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `create_user.py` fails to connect | Start the backend first (`uv run python run_backend.py`) — it owns the Postgres socket |
| Agent gets `401` from `/mcp` | Regenerate the key on MCP Access and re-export `VISION_MCP_KEY` |
| Tool call: "no active profile" | Activate a profile on the Vision Profiles page |
| First backend run errors | Include `--migrate` (creates the schema) |

More in [`USER_MANUAL.md`](./USER_MANUAL.md).
