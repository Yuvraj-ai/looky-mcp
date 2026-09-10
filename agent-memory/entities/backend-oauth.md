---
name: backend-oauth
status: done
depends_on: [[backend-auth]]
implements: Architecture §9 (Google OAuth), §28.2 (auto-link)
related_files: backend/app/auth/oauth.py, backend/tests/test_google_oauth.py, frontend/src/pages/Login.tsx
---

## What this is
Google authorization-code login: /api/auth/google/start (redirect) + /callback. id_token verified manually: RS256 against Google JWKS (PKCS1v15+SHA256), issuer, audience, expiry, email_verified. Auto-links google_sub by verified email. Unknown email → 403 with "ask an administrator" (no public signup).

## Current state
Code complete + 7 tests (provisioned-user login, auto-link, unverified-email reject, wrong-audience reject, tampered-token reject, unknown-user reject, start redirect). NOT verified against real Google — needs real GOOGLE_OAUTH_CLIENT_ID/SECRET (questions.md Q4, human-provided).

## Key decisions made while building this
- Manual id_token verification (no google-auth dependency) — cryptography lib already in tree; ~80 lines, covers iss/aud/exp/signature exactly.
- cryptography verify needs explicit padding.PKCS1v15() (default None → TypeError).
- Tests use dev-dep `rsa` lib for local keygen + monkeypatched _fetch_token/_fetch_jwks.
- Frontend: plain <a href="/api/auth/google/start"> — full-page redirect flow, no JS popup complexity.

## Known gaps / TODO
- Real-credential smoke test when GOOGLE_OAUTH_CLIENT_ID/SECRET provided (Q4).
