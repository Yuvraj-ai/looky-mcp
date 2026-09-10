"""MCP Bearer authentication (Decision #6/§9): pure-ASGI middleware on the /mcp
mount. Hashes the raw key, looks up the active credential, stores the user UUID
in a contextvar that tool handlers read. Completely separate code path from
frontend session auth."""

import contextvars
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.crypto import hash_mcp_key
from app.db import models

current_mcp_user_id: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "mcp_user_id", default=None
)


def default_session_factory_fn() -> async_sessionmaker[AsyncSession]:
    """Fresh engine lazily on first use so it binds to whatever event loop is
    running (uvicorn worker loop); cached so the process keeps one engine."""
    from app.db.session import build_session_factory

    return build_session_factory()


class _CachedSessionFactory:
    """Resolves the session factory once per process; the engine binds to the
    loop that first calls it (uvicorn's), avoiding cross-loop asyncpg usage."""

    def __init__(self):
        self._factory: async_sessionmaker[AsyncSession] | None = None

    def __call__(self) -> async_sessionmaker[AsyncSession]:
        if self._factory is None:
            self._factory = default_session_factory_fn()
        return self._factory


class McpAuthMiddleware:
    """Wraps the MCP streamable-HTTP ASGI app: resolves Bearer key → user UUID.

    session_factory_fn returns the session factory to use; indirection exists
    so tests can point the middleware at a test database."""

    def __init__(self, app, session_factory_fn=None):
        self.app = app
        self._session_factory_fn = session_factory_fn or _CachedSessionFactory()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])
        }
        auth = headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            await self._send_401(send)
            return
        raw_key = auth[len("Bearer ") :].strip()

        user_id = await self._resolve(raw_key)
        if user_id is None:
            await self._send_401(send)
            return

        token = current_mcp_user_id.set(user_id)
        try:
            await self.app(scope, receive, send)
        finally:
            current_mcp_user_id.reset(token)

    async def _resolve(self, raw_key: str) -> uuid.UUID | None:
        key_hash = hash_mcp_key(raw_key)
        factory = self._session_factory_fn()
        async with factory() as session:
            result = await session.execute(
                select(models.McpCredential.user_id).where(
                    models.McpCredential.key_hash == key_hash,
                    models.McpCredential.revoked_at.is_(None),
                )
            )
            row = result.scalar_one_or_none()
            return row

    @staticmethod
    async def _send_401(send) -> None:
        body = b'{"jsonrpc":"2.0","error":{"code":-32001,"message":"Unauthorized"},"id":null}'
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
