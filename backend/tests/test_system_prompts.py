"""System Prompts CRUD tests (Architecture §11, §26): CRUD + ownership isolation
+ delete-while-referenced → 409 with clear message (not raw DB error)."""

import uuid
from collections.abc import AsyncIterator

import pytest
from argon2 import PasswordHasher
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import models
from app.db import session as db_session_mod
from app.main import create_app


def prompt_payload() -> dict[str, str]:
    return {"title": f"Prompt {uuid.uuid4().hex[:6]}", "content": "Analyze the image carefully."}


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
async def auth_headers(db_session, client) -> dict[str, str]:
    from itsdangerous import URLSafeTimedSerializer

    from app.config import settings

    user = models.User(
        email=f"sp{uuid.uuid4().hex[:10]}@example.com",
        password_hash=PasswordHasher().hash("pw-123456"),
    )
    db_session.add(user)
    await db_session.commit()
    token = URLSafeTimedSerializer(settings.APP_SECRET_KEY).dumps(str(user.id))
    return {"Cookie": f"session={token}"}


@pytest.fixture
async def other_headers(db_session, client) -> dict[str, str]:
    from itsdangerous import URLSafeTimedSerializer

    from app.config import settings

    user = models.User(
        email=f"other{uuid.uuid4().hex[:10]}@example.com",
        password_hash=PasswordHasher().hash("pw-123456"),
    )
    db_session.add(user)
    await db_session.commit()
    token = URLSafeTimedSerializer(settings.APP_SECRET_KEY).dumps(str(user.id))
    return {"Cookie": f"session={token}"}


@pytest.fixture
async def auth_user_id(db_session) -> uuid.UUID:
    user = models.User(
        email=f"authu{uuid.uuid4().hex[:10]}@example.com",
        password_hash=PasswordHasher().hash("pw-123456"),
    )
    db_session.add(user)
    await db_session.commit()
    return user.id


@pytest.fixture
async def auth_headers_for(db_session):
    """Factory: create a user, return auth headers bound to it."""
    from itsdangerous import URLSafeTimedSerializer

    from app.config import settings

    async def _make() -> tuple[uuid.UUID, dict[str, str]]:
        user = models.User(
            email=f"fac{uuid.uuid4().hex[:10]}@example.com",
            password_hash=PasswordHasher().hash("pw-123456"),
        )
        db_session.add(user)
        await db_session.commit()
        token = URLSafeTimedSerializer(settings.APP_SECRET_KEY).dumps(str(user.id))
        return user.id, {"Cookie": f"session={token}"}

    return _make


class TestCrud:
    async def test_create_and_list(self, client, auth_headers):
        body = prompt_payload()
        resp = await client.post("/api/system-prompts", json=body, headers=auth_headers)
        assert resp.status_code == 201
        created = resp.json()
        assert created["title"] == body["title"]
        assert created["content"] == body["content"]
        assert "id" in created

        resp = await client.get("/api/system-prompts", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert any(p["id"] == created["id"] for p in items)

    async def test_get_one(self, client, auth_headers):
        created = (
            await client.post("/api/system-prompts", json=prompt_payload(), headers=auth_headers)
        ).json()
        resp = await client.get(f"/api/system-prompts/{created['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    async def test_update(self, client, auth_headers):
        created = (
            await client.post("/api/system-prompts", json=prompt_payload(), headers=auth_headers)
        ).json()
        resp = await client.put(
            f"/api/system-prompts/{created['id']}",
            json={"title": "New title", "content": "New content"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New title"

    async def test_delete(self, client, auth_headers):
        created = (
            await client.post("/api/system-prompts", json=prompt_payload(), headers=auth_headers)
        ).json()
        resp = await client.delete(f"/api/system-prompts/{created['id']}", headers=auth_headers)
        assert resp.status_code in (200, 204)
        resp = await client.get(f"/api/system-prompts/{created['id']}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_validation_requires_title_and_content(self, client, auth_headers):
        resp = await client.post("/api/system-prompts", json={"title": "x"}, headers=auth_headers)
        assert resp.status_code == 422
        resp = await client.post("/api/system-prompts", json={"content": "y"}, headers=auth_headers)
        assert resp.status_code == 422


class TestOwnership:
    async def test_cross_user_get_is_404(self, client, auth_headers, other_headers):
        created = (
            await client.post("/api/system-prompts", json=prompt_payload(), headers=auth_headers)
        ).json()
        resp = await client.get(f"/api/system-prompts/{created['id']}", headers=other_headers)
        assert resp.status_code == 404  # NOT 403 — no existence leak (§10)

    async def test_cross_user_update_is_404(self, client, auth_headers, other_headers):
        created = (
            await client.post("/api/system-prompts", json=prompt_payload(), headers=auth_headers)
        ).json()
        resp = await client.put(
            f"/api/system-prompts/{created['id']}",
            json={"title": "steal", "content": "steal"},
            headers=other_headers,
        )
        assert resp.status_code == 404

    async def test_cross_user_delete_is_404(self, client, auth_headers, other_headers):
        created = (
            await client.post("/api/system-prompts", json=prompt_payload(), headers=auth_headers)
        ).json()
        resp = await client.delete(f"/api/system-prompts/{created['id']}", headers=other_headers)
        assert resp.status_code == 404

    async def test_list_only_own(self, client, auth_headers, other_headers):
        await client.post("/api/system-prompts", json=prompt_payload(), headers=auth_headers)
        await client.post("/api/system-prompts", json=prompt_payload(), headers=other_headers)
        mine = (await client.get("/api/system-prompts", headers=auth_headers)).json()
        theirs = (await client.get("/api/system-prompts", headers=other_headers)).json()
        assert len(mine) == 1
        assert len(theirs) == 1
        assert mine[0]["id"] != theirs[0]["id"]

    async def test_requires_auth(self, client):
        resp = await client.get("/api/system-prompts")
        assert resp.status_code == 401


class TestDeleteReferenced:
    async def test_delete_while_referenced_returns_409(self, client, db_session, auth_headers_for):
        """Referenced prompt delete → 409 with profile name in message (§26)."""
        from cryptography.fernet import Fernet

        from app.config import settings

        user_id, headers = await auth_headers_for()

        prompt = models.SystemPrompt(user_id=user_id, title="Used prompt", content="content")
        db_session.add(prompt)
        await db_session.flush()

        profile = models.VisionProfile(
            user_id=user_id,
            name="My Vision Profile",
            endpoint="https://api.example.com/v1",
            model="vision-model",
            system_prompt_id=prompt.id,
            encrypted_api_key=Fernet(settings.VISION_ENCRYPTION_KEY).encrypt(b"key"),
            is_active=False,
        )
        db_session.add(profile)
        await db_session.commit()

        resp = await client.delete(f"/api/system-prompts/{prompt.id}", headers=headers)
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert "My Vision Profile" in detail
