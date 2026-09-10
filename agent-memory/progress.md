# Progress Log (append per phase)

Format: one entry per phase — completed, tests passing, next.

---

## 2026-09-10 — Phase 0: tool discovery + memory scaffolds

- Enumerated environment (see context.md "Available tooling"). Critical finding: no system Postgres → pgserver workaround (Q1).
- agent-memory/ scaffolds created: context.md, decisions.md, questions.md, progress.md, entities/.

**Next:** Phase 1 — project skeleton.

## 2026-09-10 — Phase 1: project skeleton

- Backend: pyproject (uv, Python 3.12 venv), FastAPI app factory + health route, settings from env, .env/.env.example, pgserver dev DB initialized.
- Frontend: Vite react-ts scaffold, strict TS, eslint+prettier, typed fetch client shell.
- Tests: backend health test passes (1/1); ruff/black/mypy clean; frontend build+lint+format clean.

**Next:** Phase 2 — database schema + Alembic migrations.

## 2026-09-10 — Phase 2: database + migrations

- SQLAlchemy async models for all 4 tables exactly per Architecture §5 (gen_random_uuid defaults, users CASCADE, system_prompts→vision_profiles RESTRICT, partial unique active-profile index, mcp_credentials UNIQUE(user_id)).
- Alembic wired to app settings; autogenerate ran against real Postgres; migration 3ab5256d84ee applied.
- 10/10 schema tests pass (constraints verified at DB level); ruff/black/mypy clean.
- Dev loop: `scripts/dev.py` keeps pgserver Postgres + uvicorn alive in one process.

**Next:** Phase 3 — frontend auth (email/password, session cookie, create_user script).

## 2026-09-10 — Phase 3: frontend auth

- Backend: argon2id password hashing, itsdangerous-signed session cookie (HttpOnly/SameSite=Lax/7d), /api/auth/login|logout|me, create_user.py admin script (no signup route).
- Frontend: data router with auth guards, AuthContext, Login page, Layout + 3 page stubs, /api dev proxy.
- Tests: 20/20 backend (auth API + provisioning script); ruff/black/mypy clean; frontend build+lint+format clean.
- Browser smoke test (Playwright/Chromium after human symlinked chrome binary): login→protected page→logout all verified live against real Postgres.

**Next:** Phase 4 — System Prompts CRUD (API + UI).

## 2026-09-10 — Phase 4: System Prompts CRUD

- Backend: /api/system-prompts CRUD, ownership-scoped (foreign id → 404), delete-referenced → 409 with profile names.
- Frontend: SystemPrompts page + PromptForm (create/edit/delete).
- Tests: 31/31 backend total; browser-verified CRUD round-trip.
- Lint/format/typecheck clean both sides.

**Next:** Phase 5 — Vision Profiles CRUD (needs a system prompt to exist first — verified it does).
