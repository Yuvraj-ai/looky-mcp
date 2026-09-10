---
name: api-vision-profiles
status: done
depends_on: [[api-system-prompts], [backend-auth]]
implements: Architecture §7 (activation), §11 (vision-profiles routes), §16 (profile data)
related_files: backend/app/api/vision_profiles.py, backend/app/repositories/vision_profiles.py, backend/app/crypto.py, backend/tests/test_vision_profiles.py, backend/tests/test_crypto.py, frontend/src/pages/VisionProfiles.tsx, frontend/src/pages/ProfileForm.tsx, frontend/src/api/visionProfiles.ts
---

## What this is
Vision Profiles CRUD + transactional activation. API keys Fernet-encrypted at rest, never returned (`has_api_key: true` only). Exactly-one-active enforced by DB partial unique index; activate = deactivate-others-then-activate in one commit.

## Current state
Complete. 15 tests (CRUD, key-never-in-response, blank-key-keeps-old, cross-user 404, foreign-prompt 422, activation incl. concurrent) + 4 crypto tests. Browser-verified create/activate flow.

## Key decisions made while building this
- Separate Create/Update pydantic bodies: update allows `api_key: ""` (= keep existing), create requires it.
- Activation uses two UPDATEs (exclude self from deactivate) + single commit — avoids nested `session.begin()` (session auto-begins in SQLAlchemy 2 async).
- Referencing another user's system_prompt_id on create → 422 "Unknown system prompt" (ownership validated before insert; FK would also catch).
- MCP key format implemented here too (crypto.py): `mcp_` + 43 base62 chars (32 bytes entropy), SHA-256 hash stored — per decisions.md.

## Known gaps / TODO
- None.
