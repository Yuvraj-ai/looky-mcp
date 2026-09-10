---
name: api-system-prompts
status: done
depends_on: [[backend-auth], [db-schema]]
implements: Architecture §11 (system-prompts routes), §6 (RESTRICT), §10 (ownership)
related_files: backend/app/api/system_prompts.py, backend/app/repositories/system_prompts.py, backend/tests/test_system_prompts.py, frontend/src/pages/SystemPrompts.tsx, frontend/src/pages/PromptForm.tsx, frontend/src/api/systemPrompts.ts
---

## What this is
System Prompts CRUD: REST routes (list/create/get/update/delete), ownership-scoped repository, 409 with referencing profile names on delete-while-referenced, full SPA page with create/edit/delete.

## Current state
Complete. 11 API tests pass (CRUD, 404-on-foreign-id, list-isolation, 409-referenced). Browser-verified create→edit→delete flow.

## Key decisions made while building this
- FK RESTRICT violation caught as IntegrityError → rollback → follow-up query for referencing profile names → 409 detail "This system prompt is used by profile 'X' — reassign or delete that profile first" (architecture §6 exact wording).
- Attribute values captured (prompt.id/user_id) *before* session.delete — ORM expires them post-commit/rollback and lazy loads blow up outside greenlet context.
- Test fixture `auth_headers_for` factory mints signed cookies directly (no login round-trip needed per test).

## Known gaps / TODO
- None for this component.
