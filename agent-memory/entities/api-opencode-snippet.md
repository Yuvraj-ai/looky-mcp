---
name: api-opencode-snippet
status: done
depends_on: [[api-mcp-credential]]
implements: Decision #7 §3.8, Architecture §11
related_files: backend/app/api/mcp_credential.py (opencode-snippet), backend/tests/test_opencode_snippet.py, frontend/src/pages/McpAccess.tsx, frontend/src/api/mcpCredential.ts
---

## What this is
GET /api/mcp-credential/opencode-snippet — ready-to-copy opencode.json config. Key omitted; Authorization header uses {env:VISION_MCP_KEY}; URL from PUBLIC_BASE_URL; oauth:false.

## Current state
Complete. 3 tests (shape + env ref, valid JSON, auth required). Shown in McpAccess page under key management.

## Key decisions made while building this
- Snippet built as a plain string (not json.dumps) for stable formatting; test parses it as JSON to prove validity.

## Known gaps / TODO
- None.
