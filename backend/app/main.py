"""FastAPI application factory. Mounts REST API and MCP server (Architecture §1, §21).

MCP: MCPServer.streamable_http_app() mounted at /mcp behind McpAuthMiddleware;
the session manager runs inside this app's lifespan (required — Starlette does
not run mounted sub-app lifespans). TransportSecuritySettings enables the
SDK's Origin/DNS-rebinding validation (Decision #8)."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.transport_security import TransportSecuritySettings

from app.api import auth_routes, mcp_credential, system_prompts, vision_profiles
from app.api import settings as settings_routes
from app.auth.mcp_auth import McpAuthMiddleware, _CachedSessionFactory
from app.auth.oauth import router as google_oauth_router
from app.config import settings
from app.mcp import server as mcp_server_mod
from app.mcp.server import create_mcp_server


def _mcp_transport_security() -> TransportSecuritySettings:
    """Origin validation (Decision #8): allow only our own PUBLIC_BASE_URL host
    (plus localhost forms for direct dev access); wildcard ports cover uvicorn's
    random test ports and any proxied port."""
    host = urlsplit(settings.PUBLIC_BASE_URL).hostname or "localhost"
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[host, host + ":*", "localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*"],
        allowed_origins=[settings.PUBLIC_BASE_URL],
    )


def create_app(mcp_session_factory_fn=None) -> FastAPI:
    # fresh MCPServer per app: the SDK session manager is single-use, and tests
    # build the app multiple times
    mcp = create_mcp_server()

    # 5 MB image ⇒ ~6.8 MB base64 payload + JSON envelope — raise the SDK's 4 MB
    # default. streamable_http_path="/mcp" + root mount (last route) serves
    # exactly /mcp with no trailing-slash redirect while REST routes match first.
    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        transport_security=_mcp_transport_security(),
        max_request_body_size=8 * 1024 * 1024,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title="Looky MCP", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.CORS_ALLOWED_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_routes.router)
    app.include_router(google_oauth_router)
    app.include_router(system_prompts.router)
    app.include_router(vision_profiles.router)
    app.include_router(mcp_credential.router)
    app.include_router(settings_routes.router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # mounted last: REST routes above match first. The injected factory (tests)
    # is shared by auth middleware AND tool execution so both hit the test DB.
    factory_fn = mcp_session_factory_fn or _CachedSessionFactory()
    mcp_server_mod.set_session_factory_fn(factory_fn)
    spa_fallback = _get_spa_fallback()
    app.mount("/", McpAuthMiddleware(mcp_app, session_factory_fn=factory_fn, fallback=spa_fallback))

    return app


class _SPAStaticApp:
    def __init__(self, static_dir: Path):
        self.static_dir = static_dir

    async def __call__(self, scope, receive, send):
        from starlette.responses import FileResponse, Response

        if scope["type"] != "http":
            return

        raw_path = scope.get("path", "/").lstrip("/")
        file_path = (self.static_dir / raw_path).resolve()

        # Prevent path traversal outside static_dir
        if not str(file_path).startswith(str(self.static_dir)):
            resp = Response("Forbidden", status_code=403)
            await resp(scope, receive, send)
            return

        if raw_path and file_path.is_file():
            resp = FileResponse(file_path)
            await resp(scope, receive, send)
            return

        index_file = self.static_dir / "index.html"
        if index_file.is_file():
            resp = FileResponse(index_file)
            await resp(scope, receive, send)
            return

        resp = Response("Not Found", status_code=404)
        await resp(scope, receive, send)


def _get_spa_fallback() -> _SPAStaticApp | None:
    static_env = os.environ.get("STATIC_DIR")
    if static_env and Path(static_env).is_dir():
        return _SPAStaticApp(Path(static_env).resolve())
    candidate = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if candidate.is_dir():
        return _SPAStaticApp(candidate.resolve())
    return None


app = create_app()
