# Deployment

Per Architecture §23 / Decision #8/#9:

- **Single uvicorn worker process** — deliberate: the in-memory rate limiter and
  concurrency limiter behave exactly as Decision #9 documents.
- Reverse proxy (Caddy or nginx, both provided) terminates TLS, serves the built
  SPA, and proxies `/api/*` + `/mcp` to uvicorn.
- Postgres as a normal system service or managed instance. No cluster/replicas.
- Docker is optional (Architecture §27: convenience, not a requirement).

## Files in this directory

| File | Purpose |
|---|---|
| `Dockerfile` | Backend image (Python 3.12-slim, uv-installed deps) |
| `docker-compose.yml` | Backend + Postgres for container deploys (env-driven) |
| `Caddyfile` | TLS + SPA + proxy, automatic certificates |
| `nginx.conf` | Same topology for nginx/certbot setups |
| `vision-mcp.service` | Plain systemd unit for non-Docker deploys |

## Steps (systemd + Caddy variant)

```bash
# 1. backend
cd backend
uv venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env   # fill DATABASE_URL, APP_SECRET_KEY, VISION_ENCRYPTION_KEY, PUBLIC_BASE_URL...
alembic upgrade head

# 2. frontend
cd ../frontend && npm ci && npm run build   # → dist/

# 3. provision your user
cd ../backend && python scripts/create_user.py --email you@example.com --password '...'

# 4. services
sudo cp deploy/vision-mcp.service /etc/systemd/system/
sudo systemctl enable --now vision-mcp
sudo cp deploy/Caddyfile /etc/caddy/  # edit domain + paths first
sudo systemctl reload caddy
```

## OpenCode client setup

From the app's **MCP Access** page: copy the `opencode.json` snippet, put the
generated key in the `VISION_MCP_KEY` environment variable (never in the JSON).

Status: artifacts provided; no production deployment executed (Phase 15 marked
optional/deferred in docs/deployment.md — real deploy needs a server/domain,
reserved for the operator).
