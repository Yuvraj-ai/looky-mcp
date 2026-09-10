"""OpenCode config snippet endpoint tests (Decision #7 §3.8, Architecture §11):
key NEVER embedded; uses {env:VISION_MCP_KEY}; URL from PUBLIC_BASE_URL."""

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from argon2 import PasswordHasher
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.db import models
from app.db import session as db_session_mod
from app.main import create_app


@pytest.fixture
async def client(db_engine, migrated_db) -> AsyncIterator[httpx.AsyncClient]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as s:
            yield s

    test_app = create_app()
    test_app.dependency_overrides[db_session_mod.get_db] = override_get_db
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_headers(db_session) -> dict[str, str]:
    user = models.User(
        email=f"snip{uuid.uuid4().hex[:10]}@example.com",
        password_hash=PasswordHasher().hash("pw-123456"),
    )
    db_session.add(user)
    await db_session.commit()
    token = URLSafeTimedSerializer(settings.APP_SECRET_KEY).dumps(str(user.id))
    return {"Cookie": f"session={token}"}


class TestSnippet:
    async def test_snippet_shape_and_env_ref(self, client, auth_headers):
        resp = await client.get("/api/mcp-credential/opencode-snippet", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        snippet = body["snippet"]
        assert "mcp_x" not in snippet  # never a real key
        assert "{env:VISION_MCP_KEY}" in snippet
        assert f'"{settings.PUBLIC_BASE_URL}/mcp"' in snippet
        assert '"type": "remote"' in snippet
        assert '"oauth": false' in snippet

    async def test_snippet_is_valid_json(self, client, auth_headers):
        import json

        resp = await client.get("/api/mcp-credential/opencode-snippet", headers=auth_headers)
        snippet = resp.json()["snippet"]
        parsed = json.loads(snippet)
        mcp = parsed["mcp"]["vision"]
        assert mcp["headers"]["Authorization"] == "Bearer {env:VISION_MCP_KEY}"

    async def test_requires_auth(self, client):
        resp = await client.get("/api/mcp-credential/opencode-snippet")
        assert resp.status_code == 401
