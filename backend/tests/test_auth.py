"""Auth API tests (Architecture §9, §26): login/logout/me, session enforcement, argon2.

httpx AsyncClient against the in-process app; same event loop as the DB session,
so a single engine can be shared safely.
"""

import uuid
from collections.abc import AsyncIterator

import pytest
from argon2 import PasswordHasher
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import models
from app.db import session as db_session_mod
from app.main import create_app


@pytest.fixture
def user_email() -> str:
    return f"u{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture
def password() -> str:
    return "correct-horse-battery-staple"


@pytest.fixture
def make_user(db_session, user_email, password):
    async def _make() -> models.User:
        user = models.User(
            email=user_email,
            password_hash=PasswordHasher().hash(password),
        )
        db_session.add(user)
        await db_session.commit()
        return user

    return _make


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


class TestLogin:
    async def test_login_success_sets_cookie(self, client, make_user, user_email, password):
        await make_user()
        resp = await client.post(
            "/api/auth/login", json={"email": user_email, "password": password}
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == user_email
        set_cookie = resp.headers.get("set-cookie", "")
        assert "session=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "samesite=lax" in set_cookie.lower()

    async def test_login_wrong_password_401_generic(self, client, make_user, user_email, password):
        await make_user()
        resp = await client.post("/api/auth/login", json={"email": user_email, "password": "wrong"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password"

    async def test_login_unknown_email_401(self, client, user_email):
        resp = await client.post("/api/auth/login", json={"email": user_email, "password": "x"})
        assert resp.status_code == 401

    async def test_login_malformed_body_422(self, client):
        resp = await client.post("/api/auth/login", json={"email": "a@b.c"})
        assert resp.status_code == 422


class TestSession:
    async def test_me_requires_session(self, client):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_me_after_login(self, client, make_user, user_email, password):
        await make_user()
        await client.post("/api/auth/login", json={"email": user_email, "password": password})
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == user_email
        assert "id" in body

    async def test_logout_clears_session(self, client, make_user, user_email, password):
        await make_user()
        await client.post("/api/auth/login", json={"email": user_email, "password": password})
        resp = await client.post("/api/auth/logout")
        assert resp.status_code in (200, 204)
        resp2 = await client.get("/api/auth/me")
        assert resp2.status_code == 401

    async def test_forged_cookie_rejected(self, client, make_user, user_email, password):
        await make_user()
        resp = await client.get("/api/auth/me", headers={"Cookie": "session=forged-not-signed"})
        assert resp.status_code == 401
