<!-- prettier-ignore -->
<div align="center">

<img src="./frontend/public/favicon.svg" alt="Looky MCP logo" align="center" height="64" />

# Looky MCP

Give eyes to smart open-source models without native vision support

**Connect non-vision open-source coding agents to external vision LLMs on demand** — leverage the deep engineering intellect and cost efficiency of capable open-source models (DeepSeek Coder, Qwen, Llama 3) while delegating visual tasks through a self-hosted Model Context Protocol (MCP) server.

[FastAPI](https://fastapi.tiangolo.com) • [Model Context Protocol](https://modelcontextprotocol.io) • [LangChain](https://python.langchain.com) • [React](https://react.dev) • [PostgreSQL](https://www.postgresql.org)

[Overview](#overview) • [Features](#features) • [Getting started](#getting-started) • [Using the app](#using-the-app) • [Connect an agent](#connect-an-agent) • [Deployment](#deployment) • [Project layout](#project-layout)

</div>

---

## Overview

Many of the smartest, most capable open-source LLMs (such as DeepSeek Coder, Qwen Coder, or Llama 3) are world-class software engineers, but lack native multimodal vision support. When coding agents run on these text-only models, they cannot directly inspect screenshots of layout bugs, error popups, Figma mockups, or system architecture diagrams.

**Looky MCP bridges this gap.** It operates as an MCP server that exposes `describe_image` and `ocr_image` tools to your coding agent. When visual analysis is required, Looky MCP routes the image to a dedicated vision-capable model (OpenAI GPT-4o, Claude via OpenRouter, or a local vLLM/Ollama vision endpoint) with your tailored system prompt, and returns the extracted visual intelligence directly back to your open-source model.

### Why This Matters

- **Supercharges Non-Vision Models**: Increases the versatility of powerful text-only open-source models, allowing them to solve frontend layout bugs, verify UI changes, and parse diagrams without switching models.
- **Best-of-Both-Worlds Pairing**: Pair models that have superior coding reasoning (like DeepSeek Coder) with models that excel at visual perception (like GPT-4o or specialized vision LLMs), avoiding compromises on either front.
- **Massive Cost Optimization**: Use cheap, fast, or self-hosted open-source models for 99% of your codebase generation, routing strictly visual inspection calls to vision-capable endpoints only when an image is involved.
- **Centralized Control & Privacy**: You configure system prompts, universal guidelines, and vision profiles through a clean web dashboard. Your API keys are encrypted at rest with AES-GCM and tool calls execute through your personal self-hosted gateway.

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

The **MCP Access** page provides ready-to-copy configuration snippets for OpenCode, Claude Code, and Codex.

Export your generated key first:
```bash
export VISION_MCP_KEY=mcp_...
```

### 1. OpenCode (`opencode.json`)
```json
{
  "mcp": {
    "vision": {
      "type": "remote",
      "url": "http://localhost:8000/mcp",
      "headers": { "Authorization": "Bearer {env:VISION_MCP_KEY}" }
    }
  }
}
```

### 2. Claude Code
Run via CLI:
```bash
claude mcp add --transport http vision http://localhost:8000/mcp --header "Authorization: Bearer $VISION_MCP_KEY"
```
Or add to `.mcp.json` / `~/.claude.json`:
```json
{
  "mcpServers": {
    "vision": {
      "type": "http",
      "url": "http://localhost:8000/mcp",
      "headers": { "Authorization": "Bearer ${VISION_MCP_KEY}" }
    }
  }
}
```

### 3. Codex (`~/.codex/config.toml`)
```toml
[mcp_servers.vision]
url = "http://localhost:8000/mcp"
http_headers = { "Authorization" = "Bearer ${VISION_MCP_KEY}" }
```

Tools accept standard MCP `ImageContent` objects, raw base64 strings, or `data:image/...;base64,...` data URIs.

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
