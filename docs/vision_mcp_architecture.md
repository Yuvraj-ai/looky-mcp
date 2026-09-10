# Vision MCP — Architecture & Implementation Design

Status: Architecture proposal, built on Decisions #1–#10 (all LOCKED). No implementation decisions here override those documents. Where this doc makes a new call, it is explicitly marked **NEW (Implementation Detail)** and is not a product decision.

---

## 1. Architecture Overview

```
                         ┌───────────────────┐
                         │      Browser       │
                         │  (Vite + React)    │
                         └─────────┬──────────┘
                                   │ HTTPS / REST (/api/...)
                                   ▼
┌───────────────────────────────────────────────────────────────┐
│                    Python ASGI Backend (FastAPI)               │
│                                                                 │
│  ┌───────────────┐        ┌──────────────────┐                 │
│  │ /api/*        │        │ /mcp              │                 │
│  │ Normal REST   │        │ Streamable HTTP   │◄──── OpenCode   │
│  │ (session/cookie)│      │ (Bearer MCP key)  │                 │
│  └───────┬───────┘        └────────┬──────────┘                 │
│          │                          │                           │
│          ▼                          ▼                           │
│   ┌──────────────────────────────────────────┐                  │
│   │        Shared service layer               │                  │
│   │  AuthN/AuthZ · RateLimiter · VisionService │                  │
│   │  ImageValidator · Repositories             │                  │
│   └───────────────┬────────────────────────────┘                  │
│                    │                                             │
└────────────────────┼─────────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
   PostgreSQL                LangChain ChatOpenAI
   (users, prompts,               │
    profiles, mcp_creds)          ▼
                          OpenAI-compatible Vision LLM
```

Both the REST API and the MCP endpoint live in **one process, one deployable unit** — a modular monolith, not two services. They share the database connection pool, the rate limiter's in-memory state, and the service layer. This is required by the low-resource deployment goal and by Decision #8 (MCP mounted into the same ASGI app).

---

## 2. Component Responsibilities

| Component | Owns | Must NOT do | Talks to |
|---|---|---|---|
| **Frontend** | UI state, form validation, session cookie | Never sees decrypted API keys or MCP key after first display | Backend REST API only |
| **REST API (`/api`)** | Auth (login/OAuth), CRUD for prompts/profiles, MCP key issuance | Never decrypts a Vision API key except at profile-save/vision-call time | Database, service layer |
| **MCP endpoint (`/mcp`)** | Tool contract, MCP-key auth, invokes VisionService | Never lets the caller choose profile/model/user | Service layer only |
| **Service layer** | Business rules: rate limits, active-profile resolution, prompt composition, image validation, LLM call | No transport-specific logic (no HTTP/MCP objects) | DB repositories, LangChain |
| **Database (Postgres)** | Users, prompts, profiles, MCP credential hashes | Never stores plaintext API keys or plaintext MCP keys | Backend only |
| **Vision LLM provider** | Executes the actual vision inference | — | Called via LangChain `ChatOpenAI` |

```
Frontend  ──►  REST API  ──►  Service layer  ──►  Database
OpenCode  ──►  MCP        ──►  Service layer  ──►  Vision LLM
```

The two entry points converge on the same service layer so business rules (rate limits, active-profile resolution, validation) are defined once.

---

## 3. Backend Framework Decision

**Recommendation: FastAPI**, with the official `mcp` Python SDK mounted as a sub-application.

- The MCP SDK's `FastMCP` instance exposes `.streamable_http_app()`, an ASGI app that mounts cleanly under FastAPI (`app.mount("/mcp", mcp.streamable_http_app())`). This is a documented, working pattern.
- **Known gotcha (confirmed current):** the MCP session manager needs its `lifespan` wired into FastAPI's own `lifespan`, or you get `RuntimeError: Task group is not initialized`. This is a one-time setup detail, not an architectural risk — I'll show the exact pattern in §9/§16.
- FastAPI gives Pydantic request/response validation and a dependency-injection system that's a natural fit for both session-cookie auth (`/api`) and Bearer-key auth (`/mcp`), without extra libraries.
- Plain Starlette was considered (MCP's own SDK is built on it) — rejected only because it would mean hand-rolling validation and auth wiring, adding code with no benefit here.

## 4. Frontend Stack Decision

**Recommendation: Vite + React + TypeScript**, served as a static SPA.

- **Routing:** `react-router` (data router mode) — a handful of routes (`/login`, `/system-prompts`, `/vision-profiles`, `/mcp-access`), nothing that needs a meta-framework.
- **API communication:** plain `fetch` wrapped in a small typed client; no need for React Query/SWR at this scale, but either is a fine, low-risk addition later if pagination/caching become annoying.
- **Auth handling:** the browser holds a session cookie (HttpOnly) set by the backend; the SPA just checks `/api/auth/me` on load to decide authenticated vs. login screen.
- **State management:** local component state + React Context for "current user" — no Redux/Zustand needed for a handful of CRUD screens.
- **UI:** plain CSS or a minimal utility framework (Tailwind is fine if you want it, but not required). No component-library dependency mandated.
- No SSR framework (Next.js) — nothing here needs server rendering, and it would only add deployment complexity for a private authenticated tool.

---

## 5. Database Schema

PostgreSQL, confirmed (not just leaning) — native `UUID`, partial unique indexes (needed for the "one active profile" rule), and it pairs cleanly with SQLAlchemy (async) + Alembic for migrations.

```sql
-- users: provisioned by admin script, not public signup
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT,                 -- NULL if user only uses Google OAuth
    google_sub      TEXT UNIQUE,          -- Google account identifier, NULL if unused
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- system_prompts: owned by a user
CREATE TABLE system_prompts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_system_prompts_user ON system_prompts(user_id);

-- vision_profiles: owned by a user, references a system prompt
CREATE TABLE vision_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    endpoint            TEXT NOT NULL,
    model               TEXT NOT NULL,
    system_prompt_id    UUID NOT NULL REFERENCES system_prompts(id) ON DELETE RESTRICT,
    encrypted_api_key   BYTEA NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_vision_profiles_user ON vision_profiles(user_id);

-- Enforce "exactly one active profile per user" at the DB level:
CREATE UNIQUE INDEX uq_one_active_profile_per_user
    ON vision_profiles(user_id)
    WHERE is_active = true;

-- mcp_credentials: one row per user initially
CREATE TABLE mcp_credentials (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    key_hash    TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at  TIMESTAMPTZ
);
```

**Ownership boundary:** every row that matters is reachable only via `WHERE user_id = :authenticated_user_id`. There is no code path that accepts a caller-supplied user id for these tables — the authenticated identity (from session or MCP key) is the only source of `user_id` used in queries.

`UNIQUE (user_id)` on `mcp_credentials` directly encodes "one key per user initially" at the DB level — if that ever changes to multiple keys, this constraint is the one line to remove.

---

## 6. System Prompt Deletion Semantics

**Recommendation: RESTRICT** (reflected in the schema above as `ON DELETE RESTRICT`).

Reasoning:
- `SET NULL` would leave a Vision Profile with no system prompt — but a Vision Profile *requires* a system prompt to build every request (Decision #10's request composition always includes it). A profile in that state is broken but not obviously so; it would fail at call time with a confusing error instead of failing at delete time with a clear one.
- `CASCADE` is actively dangerous here — deleting a prompt because you're cleaning it up would silently delete a Vision Profile (and possibly the user's *active* profile), which is a much bigger, unrelated side effect the user didn't ask for.
- `RESTRICT` gives the simplest, safest behavior: the delete fails immediately with a clear message ("This system prompt is used by profile 'X' — reassign or delete that profile first"). The user stays in control and nothing is silently broken.

This is a genuinely new call (the decision docs left it open) but follows directly from the "prefer the simplest safe behavior" instruction in the requirements doc.

---

## 7. Vision Profile Data Model — Notes

Already covered in §5; key points:
- `encrypted_api_key BYTEA` — ciphertext only, produced with a Fernet key (or AES-GCM) held in an environment variable, never in the DB.
- "Only one active profile" enforced by the partial unique index — no application-level race condition possible, even under concurrent requests.
- Activating a new profile = a single transaction: `UPDATE vision_profiles SET is_active = false WHERE user_id = :uid AND is_active = true; UPDATE vision_profiles SET is_active = true WHERE id = :new_id;` — wrapped so the partial index never sees two active rows at once.

## 8. MCP Credential Model — Notes

Fields kept: `id, user_id, key_hash, created_at, revoked_at`.

**`last_used_at` — NOT included.** Nothing in the locked requirements needs it (no audit/usage-tracking requirement was established), and it would require a write on every MCP request, adding load to the hot path for a value nothing reads. If usage visibility becomes an actual need later, it's a one-column migration — deferred, not designed in now.

---

## 9. Authentication Architecture

### Frontend authentication

```
Login (email/password)                Login (Google OAuth)
   │                                       │
   ▼                                       ▼
verify password_hash (argon2/bcrypt)   verify Google id_token
   │                                       │
   └───────────────┬───────────────────────┘
                    ▼
         Issue session (HttpOnly, Secure,
         SameSite=Lax cookie; signed/opaque
         session id stored server-side or as
         a signed JWT — see NEW below)
                    │
                    ▼
      Every /api/* request: session
      middleware resolves → user UUID
```

**NEW (Implementation Detail):** sessions as signed, short-lived cookies (e.g. `itsdangerous`-signed or a JWT with a short expiry + refresh-on-activity) rather than a server-side session table — this avoids adding a `sessions` table purely for the sake of it, and fits the "don't add infrastructure you don't need" principle. If session revocation-on-demand becomes a real requirement, a sessions table is a small addition later.

- **Password hashing:** argon2id (via `passlib` or `argon2-cffi`).
- **Google OAuth:** standard authorization-code flow; on success, look up `google_sub`, or if it's a first-time login for an admin-provisioned email, link the account.
- **No public signup:** the only way a `users` row is created is an admin CLI script (`create_user.py --email ... --password ...` or `--google-sub ...`), run on the server. There is no `/api/auth/register` route.

### MCP authentication

```
Authorization: Bearer mcp_xxxxxxxx
        │
        ▼
Split prefix / lookup: hash(raw_key) with the same
algorithm used at generation (e.g. SHA-256, or a KDF
if extra brute-force resistance vs. DB leak matters)
        │
        ▼
SELECT user_id FROM mcp_credentials
WHERE key_hash = :hash AND revoked_at IS NULL
        │
        ▼
Attach user_id to MCP request context
(no cookies, no session — completely separate
 code path from frontend auth)
```

Frontend session auth and MCP key auth deliberately never share code beyond "resolve to a `user_id`" — different transports, different credential types, different lifetimes.

---

## 10. Authorization Model

```
authenticated identity (session OR MCP key)
                │
                ▼
            user UUID
                │
                ▼
   every query filters: WHERE user_id = :uid
```

Applied uniformly:
- System Prompts: `SELECT/UPDATE/DELETE ... WHERE id = :id AND user_id = :uid` — a prompt ID belonging to another user simply returns 404, not 403 (avoids confirming existence of other users' resources).
- Vision Profiles: same pattern.
- MCP credentials: a user can only see/regenerate/revoke their own row (`user_id` is unique anyway).
- MCP tool calls: `user_id` comes only from the authenticated MCP key — never from a tool argument, per Decision #6.

---

## 11. API Design

| Method | Path | Purpose | Auth | Notes |
|---|---|---|---|---|
| POST | `/api/auth/login` | Email/password login | none | sets session cookie |
| GET | `/api/auth/google/start` | Begin Google OAuth | none | redirect |
| GET | `/api/auth/google/callback` | Complete OAuth | none | sets session cookie |
| POST | `/api/auth/logout` | Clear session | session | |
| GET | `/api/auth/me` | Current user info | session | |
| GET | `/api/system-prompts` | List own prompts | session | |
| POST | `/api/system-prompts` | Create prompt | session | |
| GET | `/api/system-prompts/{id}` | Get one (own) | session | 404 if not owned |
| PUT | `/api/system-prompts/{id}` | Update (own) | session | |
| DELETE | `/api/system-prompts/{id}` | Delete (own) | session | 409 if referenced (RESTRICT) |
| GET | `/api/vision-profiles` | List own profiles | session | includes `has_api_key: true`, never the key |
| POST | `/api/vision-profiles` | Create profile | session | encrypts key server-side |
| PUT | `/api/vision-profiles/{id}` | Update profile | session | key field optional (blank = unchanged) |
| DELETE | `/api/vision-profiles/{id}` | Delete profile | session | |
| POST | `/api/vision-profiles/{id}/activate` | Set as active | session | transactional swap (§7) |
| GET | `/api/mcp-credential` | Status (configured?/created date) | session | never returns key/hash |
| POST | `/api/mcp-credential/generate` | Create or regenerate | session | plaintext key returned **once** |
| POST | `/api/mcp-credential/revoke` | Revoke | session | |
| GET | `/api/mcp-credential/opencode-snippet` | Ready-to-copy config | session | key omitted, uses `{env:VISION_MCP_KEY}` |
| ANY | `/mcp` | MCP Streamable HTTP endpoint | Bearer MCP key | handled by MCP SDK, not a REST route |

Nothing beyond this list is needed for the locked requirements.

---

## 12. MCP Tool Design

```python
@mcp.tool()
async def describe_image(image: ImageContent, prompt: str) -> str:
    """Analyze/describe the contents of an image. Use for general visual
    understanding, screenshots, diagrams, UI review, etc."""
    ...

@mcp.tool()
async def ocr_image(image: ImageContent, prompt: str) -> str:
    """Extract text from an image via OCR. Use when you need the literal
    text content of an image (error messages, code, documents)."""
    ...
```

- **Arguments:** exactly `image: ImageContent` and `prompt: str`. No `user_id`, `profile_id`, `model`, `endpoint`, or `api_key` parameter exists in the tool schema — the LLM has no way to even attempt supplying them.
- **Authentication:** resolved once per MCP session/request from the `Authorization: Bearer` header (handled by ASGI middleware ahead of the tool call, not inside the tool body).
- **Return value:** plain string (the vision model's textual answer) on success. On failure, an MCP tool error with one of the stable messages from Decision #5/#10 (e.g. `"Vision request timed out"`) — never a stack trace or raw provider payload.

---

## 13. Request Lifecycle

### `describe_image`

```
OpenCode → POST /mcp (Bearer key)
   → MCP auth middleware: hash key → user_id  (401 if invalid/revoked)
   → Rate limiter: 20/60s check for user_id    (reject if exceeded)
   → Concurrency limiter: acquire 1 of 3 slots (reject if exceeded)
   → Load active Vision Profile for user_id     (error if none configured)
   → Load referenced System Prompt
   → Image validation (base64 → size → format sniff → decode → resolution)
   → Decrypt API key (in memory only)
   → Build messages: System Prompt + Extra Instructions + user prompt + image
   → ChatOpenAI(...).ainvoke(...), timeout=60, max_retries=0
   → On success: extract text → release concurrency slot → return to MCP → OpenCode
   → On failure: translate error → release concurrency slot → return MCP error → OpenCode
```

### `ocr_image`

Identical, except the message build step omits Extra Instructions:
`System Prompt + user prompt + image` (no Extra Instructions — enforced by tool identity, not by a flag the LLM controls).

The concurrency slot is released in a `finally` block so it's freed on success, provider error, or timeout alike.

---

## 14. Concurrency Implementation

**NEW (Implementation Detail).** Simplest correct approach for a single-process (or few-worker) deployment:

```python
from collections import defaultdict
import asyncio

_locks: dict[UUID, asyncio.Semaphore] = defaultdict(lambda: asyncio.Semaphore(3))

async def run_with_concurrency_limit(user_id, coro_factory):
    sem = _locks[user_id]
    if sem.locked() and sem._value == 0:   # would block — reject instead
        raise ConcurrencyLimitError()
    async with sem:
        return await coro_factory()
```

- `asyncio.Semaphore(3)` per user id gives correct increment/decrement/release semantics for free, including on exceptions (the `async with` block always releases).
- A dict keyed by `user_id`, created lazily via `defaultdict` — no pre-allocation needed, negligible memory per active user.
- **Race conditions:** none — `asyncio.Semaphore` is safe within a single event loop, which is all a single ASGI worker process has. If deployed with multiple worker processes (e.g. multiple `uvicorn` workers), each process has its own semaphore state — this is the same limitation already called out for the rate limiter (§15) and is explicitly acceptable per Decision #9 ("in-memory state is per application process").

## 15. Rate Limiter Implementation

**NEW (Implementation Detail).** Sliding window, 20 calls / rolling 60 seconds, per user:

```python
from collections import defaultdict, deque
import time, asyncio

_calls: dict[UUID, deque[float]] = defaultdict(deque)
_lock = asyncio.Lock()

async def check_rate_limit(user_id):
    now = time.monotonic()
    async with _lock:
        dq = _calls[user_id]
        while dq and now - dq[0] > 60:
            dq.popleft()
        if len(dq) >= 20:
            raise RateLimitError()
        dq.append(now)
```

- **Data structure:** a `deque` of timestamps per user — O(1) append, O(k) cleanup where k is the number of expired entries (bounded, small).
- **Cleanup:** lazy, on each check — no background sweep task needed. Memory is naturally bounded to ≤20 timestamps per active user.
- **Concurrency safety:** a single `asyncio.Lock` guarding the dict is sufficient — check-and-append is a short synchronous block, so lock contention is negligible at this scale.
- **After process restart:** all counters reset to zero — acceptable per Decision #9 (no durability requirement).
- **Multiple worker processes:** each process enforces its own 20/60s independently, so true aggregate throughput could reach `20 × N` across `N` workers. Decision #9 explicitly accepts this for v1; the deployment recommendation (§23) is a **single worker process** specifically so this limitation doesn't matter in practice.

---

## 16. Vision Service Layer

**Recommendation: one `VisionService` class**, the single seam between MCP tool handlers and everything else:

```
MCP tool handler (thin)
        │  (image, prompt, user_id, mode: "describe" | "ocr")
        ▼
VisionService.run(user_id, mode, image, prompt)
        │
        ├─► RateLimiter.check(user_id)
        ├─► ConcurrencyLimiter.acquire(user_id)
        ├─► ImageValidator.validate(image)
        ├─► VisionProfileRepository.get_active(user_id)   (404 → "No active Vision Profile configured")
        ├─► SystemPromptRepository.get(profile.system_prompt_id)
        ├─► decrypt(profile.encrypted_api_key)
        ├─► build_messages(mode, system_prompt, extra_instructions, prompt, image)
        ├─► ChatOpenAI(...).ainvoke(messages)
        └─► translate errors → stable messages
```

This is the "reasonable middle ground" the brief asked for: **one** service class orchestrating **four** narrow collaborators (`RateLimiter`, `ImageValidator`, two repositories) rather than either (a) one giant function containing everything, or (b) a dozen tiny service objects. MCP tool handlers become ~5 lines each: parse args, call `VisionService.run(...)`, return the string.

The REST API never calls `VisionService` — it only manages the data (`system_prompts`, `vision_profiles`, `mcp_credentials`) that `VisionService` later reads.

---

## 17. Image Validation Layer

**Library: Pillow (`PIL`)** — it does actual format sniffing (not trusting the extension/MIME), decoding, and gives pixel dimensions, which covers every check the requirements need without extra dependencies.

```
base64.b64decode(data)                     → reject on decode error
len(raw_bytes) <= 5 * 1024 * 1024          → reject if over
Image.open(BytesIO(raw_bytes)).format       → must be JPEG/PNG/WEBP (sniffed, not declared)
img.load()                                  → forces full decode; catches corrupt data
img.width * img.height <= 8_294_400         → (~8.3 MP) reject if over
```

**Memory note:** decoding an ~8.3 MP image as RGBA is ~32 MB of raw pixel data (per Decision #4's own table) — per in-flight request, bounded by the 3-concurrent-calls-per-user limit, so worst case per user is ~100 MB transient. This is why the resolution cap matters independently of the 5 MB encoded-size cap: a highly compressed image can still decode to much more RAM than its encoded size suggests.

No resizing/cropping/conversion is performed — the validated image bytes are passed to LangChain unmodified.

---

## 18. Vision LLM Integration

```
Vision Profile (endpoint, model, encrypted_api_key)
        │
        ▼
   decrypt in memory
        │
        ▼
ChatOpenAI(model=profile.model, api_key=decrypted,
           base_url=profile.endpoint, timeout=60, max_retries=0)
        │
        ▼
messages = [
    SystemMessage(system_prompt.content),
    HumanMessage(content=[
        {"type": "text", "text": extra_instructions + "\n" + user_prompt},  # description only
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}},
    ])
]
        │
        ▼
await model.ainvoke(messages)
        │
        ▼
response.content  →  returned to MCP
```

For OCR, the `HumanMessage` text is just `user_prompt` (no Extra Instructions concatenated in) — this is a straight `if mode == "describe"` branch in `build_messages()`, not a flag passed through to the LLM, so there's no way for Extra Instructions to leak into OCR by mistake.

---

## 19. Timeout & Error Architecture

- `timeout=60` is passed directly to `ChatOpenAI` — the underlying HTTP client enforces it; no separate `asyncio.wait_for` wrapper needed (avoids double-timeout bugs).
- Error translation happens in **one place**: a `try/except` inside `VisionService.run()`, mapping caught exception types to the stable message table from Decision #10 §14. This keeps MCP tool handlers free of error-handling logic.
- Nothing below `VisionService` (LangChain, `httpx`) is allowed to have its exception surface directly to the MCP layer — everything is caught and re-raised as one of the defined stable errors.

---

## 20. Security Architecture

| Area | Approach |
|---|---|
| Password hashing | argon2id |
| OAuth | standard Google authorization-code flow, verify `id_token` signature/audience |
| Session cookie | HttpOnly, Secure, SameSite=Lax, short expiry |
| MCP key hashing | SHA-256 (or stronger KDF) of the raw key; only the hash stored |
| API key encryption | Fernet (AES-128-CBC + HMAC) using a key from `VISION_ENCRYPTION_KEY` env var, never in DB |
| HTTPS | required at the reverse proxy (Decision #8) |
| CORS | REST API allows only the frontend's own origin; `/mcp` needs no CORS (server-to-server) |
| CSRF | mitigated by SameSite=Lax cookies + requiring `Content-Type: application/json` (not form-encoded) on state-changing routes |
| MCP Origin validation | Streamable HTTP spec requires validating the `Origin` header to prevent DNS-rebinding-style attacks — the MCP SDK's transport handles this; confirm it's enabled |
| SQL injection | parameterized queries throughout (SQLAlchemy) — no raw string interpolation |
| Authorization | every query scoped by authenticated `user_id` (§10) |
| Logging | never log decrypted API keys, raw MCP keys, or full image bytes |
| Image memory | bounded by size/resolution caps + per-user concurrency limit (§17) |
| Rate/concurrency abuse | enforced before any provider call, per Decision #9 |
| Error leakage | stable, generic error messages only (§13/§19) — no stack traces or internals returned |

This is intentionally scoped to real risks for a small, single-tenant-per-user tool — not an enterprise threat model.

---

## 21. Project Directory Structure

```
vision-mcp/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, mounts /mcp, wires lifespans
│   │   ├── config.py                # env var loading
│   │   ├── db/
│   │   │   ├── models.py            # SQLAlchemy models
│   │   │   ├── session.py
│   │   │   └── migrations/          # Alembic
│   │   ├── auth/
│   │   │   ├── session.py           # cookie auth, password hashing
│   │   │   ├── oauth.py             # Google OAuth
│   │   │   └── mcp_auth.py          # Bearer key → user_id
│   │   ├── api/
│   │   │   ├── auth_routes.py
│   │   │   ├── system_prompts.py
│   │   │   ├── vision_profiles.py
│   │   │   └── mcp_credential.py
│   │   ├── mcp/
│   │   │   ├── server.py            # FastMCP instance, tool registration
│   │   │   └── tools.py             # describe_image / ocr_image (thin)
│   │   ├── services/
│   │   │   ├── vision_service.py
│   │   │   ├── rate_limiter.py
│   │   │   ├── concurrency_limiter.py
│   │   │   └── image_validator.py
│   │   ├── repositories/
│   │   │   ├── users.py
│   │   │   ├── system_prompts.py
│   │   │   ├── vision_profiles.py
│   │   │   └── mcp_credentials.py
│   │   └── crypto.py                # Fernet encrypt/decrypt, key hashing
│   ├── scripts/
│   │   └── create_user.py           # admin provisioning
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/ (Login, SystemPrompts, VisionProfiles, McpAccess)
│   │   ├── api/ (typed fetch client)
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   └── package.json
├── docs/
│   └── (this document + the locked decision docs)
└── README.md
```

No `microservices/`, no `workers/`, no `celery/` — nothing exists in this tree without a locked requirement behind it.

---

## 22. Configuration & Environment Variables

| Variable | Purpose | Where |
|---|---|---|
| `DATABASE_URL` | Postgres connection string | env |
| `APP_SECRET_KEY` | Session cookie signing | env |
| `VISION_ENCRYPTION_KEY` | Fernet key for Vision API key encryption at rest | env, never DB |
| `GOOGLE_OAUTH_CLIENT_ID` / `_SECRET` | Google login | env |
| `PUBLIC_BASE_URL` | Used to build the OpenCode config snippet | env |
| `CORS_ALLOWED_ORIGIN` | Frontend origin | env |

Application secrets (above) live in environment variables only, never source control. **User Vision Profile API keys** are a different category entirely — user-supplied data, stored encrypted in the database, decrypted only transiently in memory during a vision call. These two categories of "secret" must never be conflated in code or docs.

---

## 23. Deployment Architecture

```
                 ┌────────────────────────┐
Internet ──HTTPS─►  Reverse proxy (nginx/  │
                 │  Caddy) — TLS + static  │
                 │  file serving for SPA   │
                 └───────────┬────────────┘
                             │
                    ┌────────┴────────┐
                    │ FastAPI (uvicorn,│
                    │ single worker)   │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │   PostgreSQL     │
                    └──────────────────┘
```

- **Single `uvicorn` worker process** — deliberate, not a limitation to work around: it makes the in-memory rate limiter and concurrency limiter behave exactly as documented in Decisions #9, with no cross-process drift. Vertical scaling (more CPU/RAM on the box) is the answer if load grows; horizontal scaling is explicitly out of scope for v1.
- Reverse proxy (nginx or Caddy) terminates TLS and serves the built frontend static files; proxies `/api/*` and `/mcp` to uvicorn.
- **Docker: optional, not mandatory.** A single `Dockerfile` for the backend is a convenience for reproducible deploys, but a plain `systemd` service running `uvicorn` directly is equally valid and has fewer moving parts on a low-spec box. Either is fine — pick whichever the deploy target's operator is more comfortable with.
- Postgres runs as a normal system service or managed instance — no cluster/replica setup implied by any requirement.

## 24. Development Environment

```
docker compose up postgres        # or a local Postgres install
cd backend && uvicorn app.main:app --reload
cd frontend && npm run dev
```

- Local MCP testing: point OpenCode's `opencode.json` at `http://localhost:8000/mcp` with a locally-generated MCP key, or use the MCP Inspector CLI (`npx @modelcontextprotocol/inspector`) against the local endpoint directly — no production infrastructure required.
- Alembic migrations run against the local Postgres the same way as production.

---

## 25. Implementation Order

Dependency-driven, not arbitrary:

```
Phase 1 — Project skeleton (backend/frontend scaffolds, config loading)
Phase 2 — Database + migrations (all four tables, constraints)
Phase 3 — Frontend auth: email/password + session cookie + admin user-provisioning script
Phase 4 — System Prompts CRUD (API + UI) — no dependencies beyond auth
Phase 5 — Vision Profiles CRUD (API + UI) — depends on System Prompts existing
Phase 6 — MCP credential issuance (API + UI) — depends on auth
Phase 7 — MCP endpoint + auth middleware — mount /mcp, verify Bearer→user_id
Phase 8 — Image validation layer (standalone, testable in isolation)
Phase 9 — Rate limiter + concurrency limiter (standalone, testable in isolation)
Phase 10 — VisionService + LangChain integration — ties 7/8/9 together
Phase 11 — describe_image / ocr_image tool wiring
Phase 12 — Google OAuth (additive, doesn't block anything else)
Phase 13 — OpenCode config snippet endpoint + docs
Phase 14 — End-to-end testing against a real OpenAI-compatible endpoint
Phase 15 — Deployment (reverse proxy, TLS, systemd/Docker)
```

Google OAuth is pushed later than the requirements doc's own phase list implied, because email/password alone is sufficient to develop and test everything else — OAuth is additive, not a dependency for other phases.

---

## 26. Testing Strategy

- **Auth:** valid/invalid login, session required on protected routes, cross-user access returns 404 not the other user's data.
- **System Prompts:** CRUD + ownership isolation; delete-while-referenced returns a 409 with a clear message (not a raw DB constraint error).
- **Vision Profiles:** CRUD; API key never appears in any response body; activating a profile always leaves exactly one active (test concurrent activation attempts too).
- **MCP:** valid key → correct user_id; invalid key → 401; revoked key → 401; regenerating invalidates the old key immediately.
- **Image validation:** valid JPEG/PNG/WebP; invalid base64; corrupted bytes; disguised format (e.g. a GIF renamed to `.jpg`, since the check is signature-based); >5MB; >8.3MP.
- **Rate limiting:** 20 allowed, 21st rejected within the window; window slides correctly after 60s.
- **Concurrency:** 3 allowed, 4th rejected; slot released after success, after a raised exception, and after a simulated timeout.
- **Vision service:** mock the LLM call for success, auth failure (401-style), timeout, 429, 5xx, and a malformed/empty response — assert each maps to its documented stable error string.

---

## 27. Locked vs. Deferred

| Item | Status | Reason |
|---|---|---|
| Backend: FastAPI + official `mcp` SDK | Implementation detail (this doc) | Simplest fit for MCP mounting + auth needs |
| Frontend: Vite + React + TS | Implementation detail (this doc) | SPA is sufficient; no SSR requirement |
| Database: PostgreSQL | Locked (confirmed here) | Native UUID, partial indexes, no reason to deviate from stated leaning |
| Schema (§5) | Implementation detail | Directly encodes the LOCKED conceptual models from Decisions #1/#6 |
| System Prompt delete = RESTRICT | New recommendation (this doc) | Simplest safe behavior per the brief's own instruction |
| Sessions as signed cookies (no session table) | Implementation detail | No revocation-on-demand requirement exists yet |
| `last_used_at` omitted | Implementation detail | No usage-tracking requirement; deferred |
| Concurrency via `asyncio.Semaphore` per user | Implementation detail | Correct, lightweight, no Redis |
| Rate limiting via per-user `deque` + lock | Implementation detail | Correct, lightweight, no Redis |
| Image lib: Pillow | Implementation detail | Covers all required checks, no extra deps |
| Single uvicorn worker | Implementation detail | Makes in-memory limiter state exactly match Decision #9's documented behavior |
| Docker | Deferred / optional | Convenience only, not required by any locked decision |
| Google OAuth built later than other phases | Implementation detail | Additive, not a blocking dependency |
| Multiple MCP keys, MCP OAuth, streaming, retries, provider fallback, custom headers, advanced model params | Deferred | Explicitly excluded by Decisions #1, #6, #9, #10 |

---

## 28. Genuine Unknowns

Going through the requirements against this design, there are two small things that are genuinely worth a decision before coding — everything else in the "not yet locked" lists across the four decision docs turned out to be resolvable as an ordinary implementation detail during this design pass (framework choices, schema shape, limiter data structures, etc.), so this list is short:

1. **Question:** MCP key hash algorithm — plain SHA-256 vs. a slow KDF (e.g. Argon2/bcrypt) for the MCP key hash?
   **Why it matters:** SHA-256 is fast to verify (good for a hot-path check on every MCP request) but offers no extra protection if the DB leaks and the key has low entropy. A slow KDF is safer against brute force but adds latency to every single MCP call.
   **Options:** (a) SHA-256 of a high-entropy random key (e.g. 32 random bytes, base62-encoded) — brute force is already infeasible due to entropy, not hash cost; (b) Argon2id, accepting the added per-request latency.
   **Recommendation:** (a) — generate the raw key with enough entropy (32+ random bytes) that a fast hash is fine, avoiding a KDF's latency on every vision call.
   **Must decide before coding?** No — easy to swap later since it's an internal implementation detail with no schema impact.

2. **Question:** Exact Google OAuth account-linking behavior — if a user's email already exists (created via admin script for password login) and they then use "Sign in with Google" with the same email, do we auto-link, or require an explicit admin step?
   **Why it matters:** Auto-linking by email match is convenient but assumes email ownership is verified (Google-verified emails generally are, so this is low-risk) — still worth being explicit about rather than implicit.
   **Options:** (a) auto-link by verified email match; (b) require the admin to pre-set `google_sub` on the user record.
   **Recommendation:** (a), since Google's `id_token` includes `email_verified` — safe to trust.
   **Must decide before coding?** No — affects a few lines in Phase 12 (OAuth), doesn't touch anything built earlier.

No other blockers were found. The decision documents already closed every question that would otherwise force a redesign.

---

## 29. Final Summary

```
                         ┌───────────────────┐
                         │     OpenCode      │
                         └─────────┬─────────┘
                                   │
                         MCP / HTTPS / Bearer
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────┐
│              FastAPI ASGI Backend (1 worker)              │
│                                                            │
│  ┌──────────────┐    ┌──────────────┐                     │
│  │ REST /api/*  │    │ MCP /mcp     │                     │
│  └──────┬───────┘    └──────┬───────┘                     │
│         └──────────┬─────────┘                            │
│                     ▼                                     │
│            Auth / AuthZ / Service layer                   │
│                     │                                     │
│          ┌──────────┴──────────┐                          │
│          ▼                     ▼                          │
│    PostgreSQL            VisionService                    │
│    (SQLAlchemy)                │                          │
│                          LangChain ChatOpenAI              │
└─────────────────────────────────┼──────────────────────────┘
                                   ▼
                        OpenAI-compatible Vision LLM
```

**Recommended stack:** FastAPI + official `mcp` SDK (backend) · Vite + React + TypeScript (frontend) · PostgreSQL + SQLAlchemy (async) + Alembic (data) · Pillow (image validation) · LangChain `ChatOpenAI` (vision calls) · nginx/Caddy + single uvicorn worker (deployment).

**Database schema, API structure, MCP structure, project layout, implementation sequence:** as detailed in §5, §11, §12, §21, §25 above.

**Remaining genuine decisions:** the two small items in §28 — neither blocks starting implementation.
