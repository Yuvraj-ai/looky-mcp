---
name: frontend-app
status: in-progress
depends_on: [[backend-app]]
implements: Architecture §4 (Vite+React+TS SPA), §21
related_files: frontend/src/App.tsx, frontend/src/api/client.ts, frontend/eslint.config.js
---

## What this is
Vite + React 19 + TypeScript SPA. Data router, AuthContext, and the four pages arrive with Phases 3–6.

## Current state
Scaffold: strict TS, eslint flat config (10) + prettier, typed fetch client shell (`src/api/client.ts`), build/lint/format/typecheck scripts wired.

## Key decisions made while building this
- Plain CSS (no Tailwind/component lib) per Architecture §4.
- react-router-dom v7 (data router) to be used from Phase 3.
- eslint needed `ecmaVersion: 2023` as a number (ESLint 10 rejects "ES2023" string).

## Known gaps / TODO
- Pages, auth context, routing — Phases 3-6.
