---
name: backend-mcp-tools
status: done
depends_on: [[backend-mcp-server], [backend-vision-service]]
implements: Decision #2 (tools), #10, Architecture §12/§13
related_files: backend/app/mcp/server.py, backend/tests/test_e2e_tools.py, frontend/src/pages/ExtraInstructionsCard.tsx, frontend/src/api/extraInstructions.ts
---

## What this is
describe_image / ocr_image wired to VisionService through the live MCP stack; stable errors surface as MCP ToolErrors (is_error=true) with the exact stable message; Extra Instructions UI on System Prompts page.

## Current state
Complete. 3 e2e tests: full roundtrip through official MCP client + real uvicorn-mounted app + mock OpenAI-compatible HTTP provider — verifies auth header, model, system prompt, image data URL at the provider, OCR excludes extra instructions, no-active-profile → stable error.

## Key decisions made while building this
- ToolError from `mcp.server.mcpserver.exceptions` (v2 SDK); SDK prefixes message with "Error executing tool <name>:" — stable strings remain intact inside.
- Session factory for tools: plain module-global set by create_app (NOT contextvar — the MCP app runs in the server thread, which starts with a fresh context; module state propagates, contextvars don't).
- e2e provider = real uvicorn HTTP server (not MockTransport) so the backend's provider call traverses the full network stack.

## Known gaps / TODO
- None for v1.
