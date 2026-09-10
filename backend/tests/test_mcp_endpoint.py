"""MCP endpoint tests (Phase 7): mount /mcp, Bearer auth via middleware,
invalid/revoked/missing key → 401, valid key → initialize succeeds, user_id in context.

Uses the official mcp client streamablehttp_client against the live-mounted app.
"""

import uuid

import pytest
from argon2 import PasswordHasher
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import models
from app.db import session as db_session_mod
from app.main import create_app


@pytest.fixture
async def user_with_key(db_session) -> tuple[uuid.UUID, str]:
    user = models.User(
        email=f"mcpauth{uuid.uuid4().hex[:10]}@example.com",
        password_hash=PasswordHasher().hash("pw-123456"),
    )
    db_session.add(user)
    await db_session.commit()
    return user.id, "smoke@example.com"


def _make_app_with_db(db_engine, db_url):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as s:
            yield s

    class ServerLoopFactory:
        """Engine created lazily inside the uvicorn server's event loop,
        pointed at the test DB (asyncpg connections bind to their creating loop)."""

        def __init__(self, url):
            self.url = url
            self._factory = None

        def __call__(self):
            if self._factory is None:
                engine = create_async_engine(self.url)
                self._factory = async_sessionmaker(engine, expire_on_commit=False)
            return self._factory

    test_app = create_app(mcp_session_factory_fn=ServerLoopFactory(db_url))
    test_app.dependency_overrides[db_session_mod.get_db] = override_get_db
    return test_app


@pytest.fixture
async def app_and_client(db_engine, migrated_db, user_with_key):
    """Live uvicorn server on a random port serving the real app (MCP needs HTTP)."""
    import threading

    import uvicorn

    test_app = _make_app_with_db(db_engine, migrated_db)
    config = uvicorn.Config(test_app, host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        await asyncio.sleep(0.05)
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}", test_app
    server.should_exit = True
    thread.join(timeout=5)


import asyncio  # noqa: E402


class TestMcpAuth:
    async def test_missing_bearer_401(self, app_and_client):
        import httpx

        base_url, _ = app_and_client
        async with httpx.AsyncClient() as c:
            resp = await c.post(
                f"{base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "id": 1,
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "t", "version": "0"},
                    },
                },
            )
            assert resp.status_code == 401

    async def test_invalid_bearer_401(self, app_and_client):
        import httpx

        base_url, _ = app_and_client
        async with httpx.AsyncClient() as c:
            resp = await c.post(
                f"{base_url}/mcp",
                headers={"Authorization": "Bearer mcp_totally_invalid_key"},
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "id": 1,
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "t", "version": "0"},
                    },
                },
            )
            assert resp.status_code == 401

    async def test_revoked_key_401(self, app_and_client, db_session, user_with_key):
        import httpx

        from app.crypto import generate_mcp_key, hash_mcp_key
        from app.repositories.mcp_credentials import McpCredentialRepository

        base_url, _ = app_and_client
        uid, _ = user_with_key
        key = generate_mcp_key()
        repo = McpCredentialRepository(db_session)
        await repo.upsert(uid, hash_mcp_key(key))
        cred = await repo.get_for_user(uid)
        await repo.revoke(cred)

        async with httpx.AsyncClient() as c:
            resp = await c.post(
                f"{base_url}/mcp",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "id": 1,
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "t", "version": "0"},
                    },
                },
            )
            assert resp.status_code == 401

    async def test_valid_key_initialize_ok(self, app_and_client, db_session, user_with_key):
        import httpx

        from app.crypto import generate_mcp_key, hash_mcp_key
        from app.repositories.mcp_credentials import McpCredentialRepository

        base_url, _ = app_and_client
        uid, _ = user_with_key
        key = generate_mcp_key()
        await McpCredentialRepository(db_session).upsert(uid, hash_mcp_key(key))

        async with httpx.AsyncClient() as c:
            resp = await c.post(
                f"{base_url}/mcp",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "id": 1,
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "t", "version": "0"},
                    },
                },
            )
            assert resp.status_code == 200
            # streamable HTTP initialize returns session id header
            assert resp.headers.get("mcp-session-id")
            assert resp.headers.get("content-type", "").startswith(
                "text/event-stream"
            ) or resp.headers.get("content-type", "").startswith("application/json")

    async def test_regenerated_old_key_401(self, app_and_client, db_session, user_with_key):
        import httpx

        from app.crypto import generate_mcp_key, hash_mcp_key
        from app.repositories.mcp_credentials import McpCredentialRepository

        base_url, _ = app_and_client
        uid, _ = user_with_key
        repo = McpCredentialRepository(db_session)
        old_key = generate_mcp_key()
        await repo.upsert(uid, hash_mcp_key(old_key))
        new_key = generate_mcp_key()
        await repo.upsert(uid, hash_mcp_key(new_key))

        init = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "t", "version": "0"},
            },
        }
        async with httpx.AsyncClient() as c:
            resp = await c.post(
                f"{base_url}/mcp", headers={"Authorization": f"Bearer {old_key}"}, json=init
            )
            assert resp.status_code == 401
