---
name: api-mcp-credential
status: done
depends_on: [[backend-auth], [db-schema]]
implements: Decision #7 (key provisioning), Architecture §11, §8
related_files: backend/app/api/mcp_credential.py, backend/app/repositories/mcp_credentials.py, backend/app/crypto.py, backend/tests/test_mcp_credential.py, frontend/src/pages/McpAccess.tsx, frontend/src/api/mcpCredential.ts
---

## What this is
MCP key lifecycle: status (never key/hash), generate (plaintext returned exactly once, only SHA-256 hash stored), revoke (idempotent). One key per user enforced by UNIQUE(user_id).

## Current state
Complete. 6 tests pass; browser-verified generate→shown-once→revoke→Not-configured.

## Key decisions made while building this
- Regenerate = UPDATE the single row (new hash, revoked_at=NULL). Can't insert a new row: UNIQUE(user_id) is unconditional (schema §5), so reuse is forced — old key invalid immediately since its hash is overwritten.
- revoke route is POST (not DELETE) — frontend client bug (used api.delete → 405) caught by browser smoke test, fixed to api.post.

## Known gaps / TODO
- OpenCode snippet endpoint arrives Phase 13.
