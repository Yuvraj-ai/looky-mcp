"""FastAPI application factory. Mounts REST API and MCP server (Architecture §1, §21).

MCP: MCPServer.streamable_http_app() mounted at /mcp behind McpAuthMiddleware;
the session manager runs inside this app's lifespan (required — Starlette does
not run mounted sub-app lifespans). TransportSecuritySettings enables the
SDK's Origin/DNS-rebinding validation (Decision #8)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.transport_security import TransportSecuritySettings

from app.api import auth_routes, mcp_credential, system_prompts, vision_profiles
from app.auth.mcp_auth import McpAuthMiddleware, _CachedSessionFactory
from app.config import settings
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

    app = FastAPI(title="Vision MCP", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.CORS_ALLOWED_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_routes.router)
    app.include_router(system_prompts.router)
    app.include_router(vision_profiles.router)
    app.include_router(mcp_credential.router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # mounted last: REST routes above match first
    app.mount(
        "/",
        McpAuthMiddleware(
            mcp_app,
            session_factory_fn=mcp_session_factory_fn or _CachedSessionFactory(),
        ),
    )

    return app


app = create_app()
