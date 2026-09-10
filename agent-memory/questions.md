# Open Questions / Items Flagged for Human Review

Format: one entry per question, with status. Never silently resolved by guessing — logged here, most conservative interpretation chosen to keep moving.

---

## Q1 — No system PostgreSQL available in this environment [RESOLVED-CONSERVATIVELY]

**Context:** Architecture assumes a Postgres connection (§24: `docker compose up postgres` or local install). This machine has no Postgres, no Docker/Podman, and sudo requires a password (can't install packages).

**Chosen path:** pip package `pgserver` — bundles official Postgres server binaries, runs entirely user-space, works with SQLAlchemy/Alembic unmodified. Used for dev DB + test fixtures.

**Residual risk:** dev binaries ≠ distro-packaged server, but they ARE the official postgres release binaries. Production deploys are unaffected (normal Postgres service per §23).

**If you disagree:** say so and I'll switch dev to whatever Postgres you provide (e.g. give me a DATABASE_URL).

---

## Q2 — Universal Extra Instructions storage location [RESOLVED-CONSERVATIVELY]

**Context:** Decisions lock "exactly one global Universal Extra Instructions prompt, describe-only" but storage/UI location was explicitly left open ("The exact frontend location for managing Universal Extra Instructions is not locked yet"). Architecture doc's §21 directory tree and §11 API table don't include it either.

**Chosen path:** singleton row in a tiny `app_settings(key,value)` table + `GET/PUT /api/settings/extra-instructions` + a settings card on the System Prompts page (closest to "settings area/page" from requirements §17). Empty allowed (= no extra instructions injected).

**Why conservative:** additive, reversible (one migration + one route group), doesn't contaminate any locked model.

---

## Q3 — Phase 14 "real OpenAI-compatible endpoint" e2e [PARTIALLY BLOCKED, needs a real key]

**Context:** Architecture §25 Phase 14: "End-to-end testing against a real OpenAI-compatible endpoint". I have no real vision-provider API credentials, and fabricating/creating an external account is exactly the kind of irreversible/external action the build prompt reserves for the human (§5).

**Chosen path:** full-stack e2e against a *mock* OpenAI-compatible server (asserts auth, limits, image passthrough, prompt composition, stable errors, JSON protocol). A real-provider e2e test exists and runs **only** when env vars `VISION_E2E_BASE_URL` / `VISION_E2E_API_KEY` / `VISION_E2E_MODEL` are set (pytest.skip otherwise).

**To fully close Phase 14:** provide those three env values (any OpenAI-compatible vision endpoint, e.g. an OpenRouter/Gemini/OpenAI key) and run `uv run pytest backend/tests/test_e2e_vision.py -k real`.

---

## Q4 — Google OAuth credentials (Phase 12) [BLOCKED-ON-HUMAN, code complete]

**Context:** Google login needs real `GOOGLE_OAUTH_CLIENT_ID`/`SECRET` from Google Cloud Console — external account creation, reserved for the human per build prompt §5.

**Status:** The authorization-code flow is fully implemented and unit/integration-tested with a fake Google JWKS/ID-token setup (signature + audience + email_verified checks, auto-link by verified email per Architecture §28.2 recommendation (a)). Wire real credentials in `.env` to go live.

---

## Q5 — Origin validation on /mcp [RESOLVED]

**Context:** Decision #8/§20 require Origin validation for the MCP Streamable HTTP transport to prevent DNS-rebinding. The MCP Python SDK does *not* currently enforce this automatically.

**Chosen path:** custom ASGI middleware on the /mcp mount: if an `Origin` header is present and its host isn't the server's own (PUBLIC_BASE_URL host or Host header), reject 403. Missing Origin (typical for OpenCode/bearer clients) allowed — bearer auth is the real gate; rebinding attackers can't send the header from a bound page.
