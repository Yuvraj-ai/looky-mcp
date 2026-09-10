---
name: context
status: in-progress
depends_on: []
implements: Build prompt §2 (memory root node)
---

# Agent Memory — Root Context

**Read this file first, every session.** Vision MCP build in progress.

- **Goal:** Python/FastAPI backend (REST + MCP server in one ASGI process) + Vite/React/TS frontend + PostgreSQL. See `docs/vision_mcp_architecture.md` (the architecture) and `docs/vision_mcp_decisions_*.md` (LOCKED product decisions #1–#10).
- **Priority order:** locked decisions > architecture doc (§27 "Implementation Detail" rows are buildable as written) > build prompt process rules.
- **Forbidden:** Redis, Kafka, Celery, microservices, LangGraph, RAG/vector DBs, agent frameworks, Docker-as-requirement.

## Available tooling (verified 2026-09-10)

- **Python 3.14.7** at `/usr/bin/python3`; **uv 0.11.9** at `~/.local/bin/uv` (use uv for venvs/deps).
- **Node v26.8.1**, npm/npx available.
- **PostgreSQL: NOT INSTALLED** on this machine. No psql, no server, no Docker/Podman, `sudo` requires a password (cannot install system packages). Nothing listening on :5432.
  - → Workaround (logged in questions.md): pip-installable **`pgserver`** wheel (bundles real Postgres binaries, user-space) for dev + tests. Production deploys still assume real Postgres per architecture §23.
- **Network:** PyPI + npm reachable.
- **Lint/format:** ruff+black and eslint+prettier installed as project dev-deps via uv/npm.
- **Tests:** pytest via uv (`uv run pytest` in `backend/`). Frontend: vitest where logic warrants it.
- **Browser automation** (Playwright MCP) available for frontend smoke checks.

## Entity index (one-line status)

Maintained in `progress.md` as phases complete; each entity file links back here.

## Phase status

See `progress.md` (append-only phase log) and `decisions.md` (build-time calls).

## Key runtime facts

- Dev DB: pgserver-managed Postgres (user-space, real server binaries). `DATABASE_URL` in `.env`.
- Backend dev server: `uvicorn app.main:app --reload` (port 8000).
- Frontend dev: `npm run dev` in `frontend/` (port 5173).
