# Deployment (Phase 15) — Optional / Deferred

Per Architecture §23:
- Single `uvicorn` worker process (deliberate, makes in-memory limiter state match Decision #9)
- Docker optional; plain `systemd` service running `uvicorn` is equally valid
- Reverse proxy (nginx/Caddy) terminates TLS and serves static SPA files
- Postgres runs as normal system service or managed instance
- No cluster/replica setup implied

Current state: deployment artifacts complete in `deploy/` (Dockerfile,
docker-compose.yml, Caddyfile, nginx.conf, vision-mcp.service, README with
steps). No production deployment executed — requires a real server/domain/TLS,
reserved for the operator. See `deploy/README.md`.
