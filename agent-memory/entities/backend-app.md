---
name: backend-app
status: done
depends_on: []
implements: Architecture §21 (project tree), §1 (single ASGI process)
related_files: backend/app/main.py, backend/app/config.py, backend/pyproject.toml
---

## What this is
FastAPI app factory + config loading; the single deployable that will host /api and /mcp.

## Current state
Skeleton only: health route, CORS, settings from env (.env checked in as .env.example). /mcp mount lands in Phase 7.

## Key decisions made while building this
- Python 3.12 venv via uv (host is 3.14 but pgserver only ships cp312 wheels — see decisions.md 2026-09-10).
- mypy pydantic plugin instead of per-callsite type: ignores.
- Dev secrets generated once into backend/.env (never committed); .pgdata/ is the pgserver data dir (gitignored).

## Known gaps / TODO
- Lifespan currently empty — MCP session manager wiring arrives Phase 7.
