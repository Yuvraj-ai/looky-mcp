# Deployment (Phase 15) — Optional / Deferred

Per Architecture §23:
- Single `uvicorn` worker process (deliberate, makes in-memory limiter state match Decision #9)
- Docker optional; plain `systemd` service running `uvicorn` is equally valid
- Reverse proxy (nginx/Caddy) terminates TLS and serves static SPA files
- Postgres runs as normal system service or managed instance
- No cluster/replica setup implied

Current state: `Dockerfile` provided for convenience; no production deployment executed.
