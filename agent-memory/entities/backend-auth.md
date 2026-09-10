---
name: backend-auth
status: done
depends_on: [[db-schema], [backend-app]]
implements: Architecture §9 (auth), §10 (authorization), §11 (auth routes)
related_files: backend/app/auth/passwords.py, backend/app/auth/session.py, backend/app/api/auth_routes.py, backend/app/repositories/users.py, backend/scripts/create_user.py, backend/tests/test_auth.py, backend/tests/test_create_user_script.py
---

## What this is
Email/password auth: argon2id hashing, itsdangerous-signed HttpOnly session cookie, login/logout/me routes, admin-only user provisioning script. No public signup route exists.

## Current state
Complete for Phase 3. 8 auth API tests + 2 script tests pass; browser smoke test passed (login → protected route → logout via Playwright/Chromium).

## Key decisions made while building this
- Tests use httpx AsyncClient + ASGITransport (NOT TestClient) — one event loop shared with the DB engine fixtures; TestClient's portal loop caused "Future attached to a different loop" with asyncpg.
- `secure` cookie flag is conditional on PUBLIC_BASE_URL scheme (http:// local dev can't set Secure + still work over plain HTTP).
- Login error is generic "Invalid email or password" for both unknown-email and wrong-password (no user enumeration).
- create_user.py accepts --database-url and converts pg8000 test URLs → asyncpg internally.
- email-validator rejects `.local`/`.test` TLDs in EmailStr — tests use `@example.com`.
- ruff B008 ignored (FastAPI Depends-in-default is the framework idiom).
- Chromium for Playwright MCP: user symlinked downloaded playwright chromium to /opt/google/chrome/chrome (needed root, human ran it — Option A).

## Known gaps / TODO
- Google OAuth arrives Phase 12 (additive).
- CSRF: SameSite=Lax + JSON content-type (architecture §20) is the mitigation; no token layer.
