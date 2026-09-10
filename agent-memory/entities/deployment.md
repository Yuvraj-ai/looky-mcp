---
name: deployment
status: done
depends_on: [[backend-app], [frontend-app]]
implements: Architecture §23, Decision #8/#9
related_files: deploy/Dockerfile, deploy/docker-compose.yml, deploy/Caddyfile, deploy/nginx.conf, deploy/vision-mcp.service, deploy/README.md, docs/deployment.md
---

## What this is
Deployment artifacts for the single-worker architecture: Dockerfile + compose (optional), systemd unit (non-Docker), Caddy + nginx reverse proxy configs (TLS + SPA + /api + /mcp proxying).

## Current state
Artifacts complete and consistent with the architecture (single worker, 8MB client_max_body_size for base64 images, MCP no-buffering). NOT deployed to any real host — execution reserved for the operator (server/domain/TLS are irreversible external actions).

## Key decisions made while building this
- **alembic env.py now auto-converts the app's asyncpg URL to pg8000** (sync driver needed by alembic) — this removed all the Phase-2 URL-swapping hacks; pg8000 moved to runtime deps (needed in prod image for migrations).
- Compose runs `alembic upgrade head` before uvicorn — works now thanks to the env.py fix.
- systemd unit includes basic hardening (ProtectSystem=strict + ReadWritePaths).
- nginx sets `client_max_body_size 8m` and `proxy_buffering off` for /mcp (SSE stream).

## Known gaps / TODO
- Real deployment execution (operator).
