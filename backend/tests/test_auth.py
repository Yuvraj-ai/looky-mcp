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


class TestDeleteAccount:
    async def test_delete_account_requires_auth(self, client):
        resp = await client.request("DELETE", "/api/auth/me", json={"confirm_email": "nobody@example.com"})
        assert resp.status_code == 401

    async def test_delete_account_rejects_email_mismatch(self, client, make_user, user_email, password):
        await make_user()
        await client.post("/api/auth/login", json={"email": user_email, "password": password})
        resp = await client.request("DELETE", "/api/auth/me", json={"confirm_email": "wrong@example.com"})
        assert resp.status_code == 400
        assert "Confirmation email does not match" in resp.json()["detail"]

    async def test_delete_account_removes_user_and_only_their_data(
        self, client, db_session, make_user, user_email, password
    ):
        from sqlalchemy import select
        from app.crypto import encrypt_api_key

        # Create target User A
        user_a = await make_user()

        # Create another User B (to verify isolation)
        user_b_email = "user_b_other@example.com"
        user_b = models.User(
            email=user_b_email,
            password_hash=PasswordHasher().hash("secret-password-b"),
        )
        db_session.add(user_b)
        await db_session.commit()

        # Add data for User A: system prompt, vision profile, mcp credential
        prompt_a = models.SystemPrompt(user_id=user_a.id, title="Prompt A", content="Content A")
        db_session.add(prompt_a)
        await db_session.flush()

        profile_a = models.VisionProfile(
            user_id=user_a.id,
            name="Profile A",
            endpoint="https://api.openai.com/v1",
            model="gpt-4o",
            system_prompt_id=prompt_a.id,
            encrypted_api_key=encrypt_api_key("sk-test-key-a"),
            is_active=True,
        )
        cred_a = models.McpCredential(user_id=user_a.id, key_hash="hash-a")
        db_session.add_all([profile_a, cred_a])

        # Add data for User B: system prompt, vision profile, mcp credential
        prompt_b = models.SystemPrompt(user_id=user_b.id, title="Prompt B", content="Content B")
        db_session.add(prompt_b)
        await db_session.flush()

        profile_b = models.VisionProfile(
            user_id=user_b.id,
            name="Profile B",
            endpoint="https://api.openai.com/v1",
            model="gpt-4o-mini",
            system_prompt_id=prompt_b.id,
            encrypted_api_key=encrypt_api_key("sk-test-key-b"),
            is_active=True,
        )
        cred_b = models.McpCredential(user_id=user_b.id, key_hash="hash-b")
        db_session.add_all([profile_b, cred_b])
        await db_session.commit()

        # Save IDs into local variables
        user_a_id = user_a.id
        prompt_a_id = prompt_a.id
        profile_a_id = profile_a.id
        user_b_id = user_b.id
        prompt_b_id = prompt_b.id
        profile_b_id = profile_b.id

        # Log in as User A
        await client.post("/api/auth/login", json={"email": user_email, "password": password})

        # User A requests deletion with exact matching email (case-insensitive test)
        resp = await client.request(
            "DELETE", "/api/auth/me", json={"confirm_email": user_email.upper()}
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "deleted"}

        # Session cookie was cleared
        set_cookie = resp.headers.get("set-cookie", "")
        assert "session=" in set_cookie
        assert "Max-Age=0" in set_cookie or 'expires=' in set_cookie.lower()

        # Subsequent GET /me fails
        resp_me = await client.get("/api/auth/me")
        assert resp_me.status_code == 401

        # Expire local test session identity map so queries hit the database
        db_session.expire_all()

        # Check database: User A data is completely gone
        res_user_a = await db_session.get(models.User, user_a_id)
        assert res_user_a is None

        res_prompt_a = await db_session.get(models.SystemPrompt, prompt_a_id)
        assert res_prompt_a is None

        res_profile_a = await db_session.get(models.VisionProfile, profile_a_id)
        assert res_profile_a is None

        res_cred_a = await db_session.execute(
            select(models.McpCredential).where(models.McpCredential.user_id == user_a_id)
        )
        assert res_cred_a.scalar_one_or_none() is None

        # CRUCIAL ISOLATION CHECK: User B data is 100% INTACT!
        res_user_b = await db_session.get(models.User, user_b_id)
        assert res_user_b is not None
        assert res_user_b.email == user_b_email

        res_prompt_b = await db_session.get(models.SystemPrompt, prompt_b_id)
        assert res_prompt_b is not None
        assert res_prompt_b.title == "Prompt B"

        res_profile_b = await db_session.get(models.VisionProfile, profile_b_id)
        assert res_profile_b is not None
        assert res_profile_b.name == "Profile B"

        res_cred_b = await db_session.execute(
            select(models.McpCredential).where(models.McpCredential.user_id == user_b_id)
        )
        assert res_cred_b.scalar_one_or_none() is not None
