# Build Decisions Ledger (append-only)

Format: `## YYYY-MM-DD — <short title>` + 2–3 lines: what, why, affects.

---

## 2026-09-10 — Dev/test Postgres via pgserver wheel

**What:** No system Postgres available (no psql, no Docker, sudo password-locked). Use pip package `pgserver` (bundles official postgres server binaries, runs user-space) for dev DB and pytest fixtures.
**Why:** Architecture requires real Postgres features (UUID, partial unique indexes); pgserver runs the genuine server without root.
**Affects:** Dev/test infra only. Production deployment (Phase 15) still assumes a real Postgres service per Architecture §23. Flagged in questions.md.

## 2026-09-10 — MCP key format: `mcp_` + 32 base62 chars, SHA-256 hash

**What:** Raw key = `mcp_` + 43-char base62 of 32 random bytes (secrets.token_urlsafe-style base62 via secrets.choice). Store only `sha256(raw).hexdigest()`.
**Why:** Architecture §28.1 recommends option (a): high-entropy key + fast hash. 32 bytes entropy makes brute force infeasible without KDF latency.
**Affects:** `backend/app/crypto.py`, mcp_credentials table usage. Swappable later; no schema impact (key_hash TEXT).

## 2026-09-10 — Session cookies: itsdangerous-signed `user_id` + expiry, 7-day sliding

**What:** Signed cookie (itsdangerous TimestampSigner, APP_SECRET_KEY) carrying user UUID; max_age 7 days, re-set on activity. No session table.
**Why:** Architecture §9 NEW (Implementation Detail) prescribes signed short-lived cookies, no sessions table.
**Affects:** `backend/app/auth/session.py`.

## 2026-09-10 — Universal Extra Instructions stored as singleton row in `app_settings`

**What:** `app_settings(key TEXT PK, value TEXT)` table holds `universal_extra_instructions` (one global row). Exposed via `GET/PUT /api/settings/extra-instructions`. Empty string allowed (= disabled).
**Why:** Requirements demand exactly one global Extra Instructions prompt (describe-only); decisions leave storage "still to be decided"; a singleton settings table is the smallest faithful representation and avoids per-user duplication (it is global, not user-owned).
**Affects:** schema (5th table via migration 0002), `backend/app/api/settings.py`, VisionService message build. Noted in questions.md as an interpretation worth confirming.

## 2026-09-10 — Vision LLM client: langchain-openai ChatOpenAI

**What:** `langchain-openai` package's `ChatOpenAI(model=..., api_key=..., base_url=..., timeout=60, max_retries=0)`.
**Why:** Decision #10 locks LangChain + OpenAI-compatible interface; `langchain-openai` is the current canonical OpenAI chat integration.
**Affects:** `backend/app/services/vision_service.py`, pyproject deps.

## 2026-09-10 — MCP mounted via FastMCP.streamable_http_app() + shared lifespan

**What:** `mcp = FastMCP("vision", stateless_http=False)`; `app.mount("/mcp", mcp.streamable_http_app())`; session manager run loop started inside FastAPI lifespan via `mcp.session_manager.run()`.
**Why:** Architecture §3 documented pattern; SDK requires lifespan wiring to avoid "Task group is not initialized".
**Affects:** `backend/app/main.py`, `backend/app/mcp/server.py`. Bearer auth enforced by an ASGI middleware on the mounted sub-app + contextvar read in tool handlers.

## 2026-09-10 — MCP Bearer auth via pure-ASGI middleware on the /mcp mount

**What:** Instead of FastAPI dependencies (sub-app has no DI access), a small pure-ASGI middleware wraps the streamable-HTTP app: reads Authorization header, hashes key, DB lookup → stores user_id in a contextvar; tools read contextvar.
**Why:** MCP SDK tools run inside the sub-app's task group; contextvars propagate correctly; avoids transport-specific logic in tools (architecture §2 "service layer" boundary preserved).
**Affects:** `backend/app/auth/mcp_auth.py`, `backend/app/mcp/tools.py`.

## 2026-09-10 — Provider error mapping uses openai SDK exception taxonomy

**What:** Catch `openai.AuthenticationError`→"Vision Profile authentication failed", `openai.RateLimitError`→"Vision service rate limit reached", `openai.APIStatusError` (5xx)→"Vision service temporarily unavailable", `openai.APITimeoutError`→"Vision request timed out", `openai.APIConnectionError`→"Vision service unavailable", 404/400→"Vision Profile configuration is invalid"/"Vision request rejected", empty content→"Vision service returned invalid response".
**Why:** Decision #10 §14 table requires these stable strings; langchain-openai re-raises openai SDK exceptions, so catching openai's taxonomy is the exact seam.
**Affects:** `backend/app/services/vision_service.py` error translation.

## 2026-09-10 — Frontend: plain CSS, react-router data router, typed fetch client

**What:** No Tailwind/component lib. `createBrowserRouter`, AuthContext + `useAuth`, `api/client.ts` typed fetch wrapper.
**Why:** Architecture §4: no meta-framework, minimal deps.
**Affects:** `frontend/src/**`.

## 2026-09-10 — Frontend lint: eslint flat config + prettier, tsc --noEmit for typecheck

**What:** eslint 9 flat config with typescript-eslint, prettier for formatting; `npm run lint`, `npm run typecheck`, `npm run build` (tsc -b) all wired in package.json.
**Why:** Build prompt §3 requires eslint+prettier and strict TS.
**Affects:** frontend package.json scripts.

## 2026-09-10 — E2E vision test targets mock OpenAI-compatible server, real-provider test opt-in

**What:** Phase 14 e2e uses a local mock OpenAI-compatible chat endpoint (httpx-based test server asserting the image part arrives). A separate e2e against a real provider runs only when `VISION_E2E_BASE_URL`, `VISION_E2E_API_KEY`, `VISION_E2E_MODEL` env vars are set; otherwise skipped.
**Why:** No real vision-provider account/credentials should be fabricated; mock e2e validates the full stack (auth→limits→validation→LangChain→provider protocol→response) without secrets.
**Affects:** `backend/tests/test_e2e_vision.py`.

## 2026-09-10 — Phase 15 deliverables: Dockerfile + docker-compose.yml + Caddy file + systemd unit + nginx sample

**What:** Deployment artifacts written as files (no live deployment executed).
**Why:** Actual production deployment requires a server, domain, TLS certs — irreversible/external actions reserved for the human per build prompt §5. docs/deployment.md already declares Phase 15 optional/deferred; artifacts make it executable when ready.
**Affects:** `deploy/` directory, `docs/deployment.md`.
