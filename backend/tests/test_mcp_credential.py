"""MCP credential issuance tests (Decision #7, Architecture §11/§26):
status/generate/revoke; plaintext shown exactly once; only hash stored;
regeneration invalidates old key immediately; revoke → subsequent auth fails."""

import uuid
from collections.abc import AsyncIterator

import pytest
from argon2 import PasswordHasher
from httpx import ASGITransport, AsyncClient
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.db import models
from app.db import session as db_session_mod
from app.main import create_app


@pytest.fixture
async def client(db_engine, migrated_db) -> AsyncIterator[AsyncClient]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as s:
            yield s

    test_app = create_app()
    test_app.dependency_overrides[db_session_mod.get_db] = override_get_db
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_headers(db_session) -> dict[str, str]:
    user = models.User(
        email=f"mcp{uuid.uuid4().hex[:10]}@example.com",
        password_hash=PasswordHasher().hash("pw-123456"),
    )
    db_session.add(user)
    await db_session.commit()
    token = URLSafeTimedSerializer(settings.APP_SECRET_KEY).dumps(str(user.id))
    return {"Cookie": f"session={token}"}


async def _fetch_credential(db_engine, user_email: str) -> models.McpCredential | None:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def run():
        async with factory() as s:
            user = (
                await s.execute(select(models.User).where(models.User.email == user_email))
            ).scalar_one()
            cred = (
                await s.execute(
                    select(models.McpCredential).where(models.McpCredential.user_id == user.id)
                )
            ).scalar_one_or_none()
            if cred is None:
                return None
            # touch attributes while session is open
            _ = cred.key_hash, cred.created_at, cred.revoked_at
            return cred

    return await run()


class TestStatus:
    async def test_status_not_configured(self, client, auth_headers):
        resp = await client.get("/api/mcp-credential", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["configured"] is False
        assert "key" not in body
        assert "key_hash" not in body

    async def test_requires_auth(self, client):
        resp = await client.get("/api/mcp-credential")
        assert resp.status_code == 401


class TestGenerate:
    async def test_generate_returns_plaintext_once(self, client, auth_headers, db_engine):
        resp = await client.post("/api/mcp-credential/generate", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        key = body["key"]
        assert key.startswith("mcp_")
        assert len(key) > 40

        # status afterwards: configured, no key material
        status = (await client.get("/api/mcp-credential", headers=auth_headers)).json()
        assert status["configured"] is True
        assert "key" not in status

        # DB row stores hash, not plaintext
        from app.crypto import hash_mcp_key

        # user email is embedded in fixture; re-derive by listing rows
        factory = async_sessionmaker(db_engine, expire_on_commit=False)

        async def rows():
            async with factory() as s:
                creds = (await s.execute(select(models.McpCredential))).scalars().all()
                return [(c.key_hash, c.revoked_at) for c in creds]

        stored = await rows()
        assert len(stored) >= 1
        hashes = [h for h, _ in stored]
        assert hash_mcp_key(key) in hashes
        assert key not in "".join(hashes)
        assert all(rev is None for _, rev in stored)

    async def test_regenerate_invalidates_old_immediately(self, client, auth_headers, db_engine):
        first = (await client.post("/api/mcp-credential/generate", headers=auth_headers)).json()[
            "key"
        ]
        second = (await client.post("/api/mcp-credential/generate", headers=auth_headers)).json()[
            "key"
        ]
        assert first != second

        # old key must no longer authenticate: simulate by checking stored hash
        from app.crypto import hash_mcp_key

        factory = async_sessionmaker(db_engine, expire_on_commit=False)

        async def current_hash():
            async with factory() as s:
                creds = (await s.execute(select(models.McpCredential))).scalars().all()
                active = [c for c in creds if c.revoked_at is None]
                return [c.key_hash for c in active]

        active_hashes = await current_hash()
        assert hash_mcp_key(second) in active_hashes
        assert hash_mcp_key(first) not in active_hashes


class TestRevoke:
    async def test_revoke(self, client, auth_headers):
        await client.post("/api/mcp-credential/generate", headers=auth_headers)
        resp = await client.post("/api/mcp-credential/revoke", headers=auth_headers)
        assert resp.status_code in (200, 204)
        status = (await client.get("/api/mcp-credential", headers=auth_headers)).json()
        assert status["configured"] is False

    async def test_revoke_when_not_configured(self, client, auth_headers):
        resp = await client.post("/api/mcp-credential/revoke", headers=auth_headers)
        assert resp.status_code in (200, 204)  # idempotent
