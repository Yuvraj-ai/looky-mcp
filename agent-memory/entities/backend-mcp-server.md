---
name: backend-mcp-server
status: done
depends_on: [[api-mcp-credential], [backend-auth]]
implements: Decision #8 (transport), Architecture §3, §12 (tools), §9 (MCP auth)
related_files: backend/app/main.py, backend/app/mcp/server.py, backend/app/auth/mcp_auth.py, backend/tests/test_mcp_endpoint.py
---

## What this is
MCP endpoint at /mcp: MCPServer (mcp SDK v2) streamable HTTP app mounted in the FastAPI process behind a pure-ASGI Bearer-auth middleware; describe_image/ocr_image registered with exactly (image: ImageContent, prompt: str).

## Current state
Complete for Phase 7 (tool bodies call VisionService, which is built in Phase 10 — currently the tools import lazily so listing works without it). 5 endpoint tests + live official-client smoke (initialize, tools/list = both tools) pass.

## Key decisions made while building this
- **mcp SDK is v2**: `MCPServer` (not FastMCP), `mcp.server.transport_security.TransportSecuritySettings`, client import `mcp.client.streamable_http_client`. Session manager is single-use → `create_mcp_server()` builds a fresh instance per `create_app()` (tests build the app repeatedly).
- Mount: `streamable_http_app(streamable_http_path="/mcp")` mounted at `/` **as the last route** — serves exactly /mcp with no 307 trailing-slash redirect; REST routes match first.
- `max_request_body_size` raised 4MB→8MB (5MB image ≈ 6.8MB base64).
- Transport security (Decision #8 Origin validation): SDK's `TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=[host, host:*, localhost…], allowed_origins=[PUBLIC_BASE_URL])` — wildcards needed because Host includes the port.
- Auth middleware is pure ASGI (sub-app has no FastAPI DI): Bearer → SHA-256 → mcp_credentials lookup → contextvar `current_mcp_user_id`; tools read the contextvar, never an argument (Decision #6).
- Middleware DB access needs an engine **bound to uvicorn's loop**: `_CachedSessionFactory` creates the engine lazily on first request (in the serving loop). Tests inject `mcp_session_factory_fn` creating a fresh engine in the server-thread loop pointed at the test DB (asyncpg binds connections to their creating loop — the classic cross-loop trap).
- Initialize responses are SSE (text/event-stream) — test asserts status + mcp-session-id header, not body JSON.

## Known gaps / TODO
- Tool *execution* (VisionService.run) lands Phase 10/11.
