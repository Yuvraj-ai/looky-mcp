"""Vision Profiles CRUD tests (Architecture §11, §26): CRUD, key never in responses,
activation always leaves exactly one active, concurrency-safe activate, foreign id → 404."""

import asyncio
import uuid
from collections.abc import AsyncIterator

import pytest
from argon2 import PasswordHasher
from httpx import ASGITransport, AsyncClient
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import func, select
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
async def user_factory(db_session):
    async def _make() -> tuple[uuid.UUID, dict[str, str]]:
        user = models.User(
            email=f"vp{uuid.uuid4().hex[:10]}@example.com",
            password_hash=PasswordHasher().hash("pw-123456"),
        )
        db_session.add(user)
        await db_session.commit()
        token = URLSafeTimedSerializer(settings.APP_SECRET_KEY).dumps(str(user.id))
        return user.id, {"Cookie": f"session={token}"}

    return _make


@pytest.fixture
async def prompt_factory(db_session):
    async def _make(user_id: uuid.UUID) -> models.SystemPrompt:
        prompt = models.SystemPrompt(
            user_id=user_id, title=f"P{uuid.uuid4().hex[:6]}", content="content"
        )
        db_session.add(prompt)
        await db_session.commit()
        return prompt

    return _make


def profile_payload(prompt_id) -> dict[str, str]:
    return {
        "name": f"Profile {uuid.uuid4().hex[:6]}",
        "endpoint": "https://api.example.com/v1",
        "model": "vision-model-x",
        "api_key": "sk-plain-key-never-store-me",
        "system_prompt_id": str(prompt_id),
    }


class TestCrud:
    async def test_create_response_has_no_api_key(self, client, user_factory, prompt_factory):
        user_id, headers = await user_factory()
        prompt = await prompt_factory(user_id)
        resp = await client.post(
            "/api/vision-profiles", json=profile_payload(prompt.id), headers=headers
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"]
        assert body["has_api_key"] is True
        assert "api_key" not in body
        assert "encrypted_api_key" not in body
        assert body["is_active"] is False

    async def test_list_never_exposes_key_material(self, client, user_factory, prompt_factory):
        user_id, headers = await user_factory()
        prompt = await prompt_factory(user_id)
        await client.post("/api/vision-profiles", json=profile_payload(prompt.id), headers=headers)
        resp = await client.get("/api/vision-profiles", headers=headers)
        assert resp.status_code == 200
        raw = resp.text
        assert "sk-plain-key-never-store-me" not in raw
        assert "api_key" not in raw.replace("has_api_key", "")
        for item in resp.json():
            assert "has_api_key" in item and item["has_api_key"] is True

    async def test_update_blank_key_keeps_old(
        self, client, user_factory, prompt_factory, db_session
    ):
        """PUT with empty api_key = unchanged key (Architecture §11)."""

        user_id, headers = await user_factory()
        prompt = await prompt_factory(user_id)
        created = (
            await client.post(
                "/api/vision-profiles", json=profile_payload(prompt.id), headers=headers
            )
        ).json()
        resp = await client.put(
            f"/api/vision-profiles/{created['id']}",
            json={**profile_payload(prompt.id), "name": "Renamed", "api_key": ""},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

        factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
        async with factory() as s:
            profile = await s.get(models.VisionProfile, uuid.UUID(created["id"]))
            assert profile is not None
            from app.crypto import decrypt_api_key

            assert decrypt_api_key(profile.encrypted_api_key) == "sk-plain-key-never-store-me"

    async def test_update_with_new_key_replaces(
        self, client, user_factory, prompt_factory, db_session
    ):
        from app.crypto import decrypt_api_key

        user_id, headers = await user_factory()
        prompt = await prompt_factory(user_id)
        created = (
            await client.post(
                "/api/vision-profiles", json=profile_payload(prompt.id), headers=headers
            )
        ).json()
        await client.put(
            f"/api/vision-profiles/{created['id']}",
            json={**profile_payload(prompt.id), "api_key": "sk-brand-new-key"},
            headers=headers,
        )
        factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
        async with factory() as s:
            profile = await s.get(models.VisionProfile, uuid.UUID(created["id"]))
            assert decrypt_api_key(profile.encrypted_api_key) == "sk-brand-new-key"

    async def test_delete(self, client, user_factory, prompt_factory):
        user_id, headers = await user_factory()
        prompt = await prompt_factory(user_id)
        created = (
            await client.post(
                "/api/vision-profiles", json=profile_payload(prompt.id), headers=headers
            )
        ).json()
        resp = await client.delete(f"/api/vision-profiles/{created['id']}", headers=headers)
        assert resp.status_code in (200, 204)
        assert (await client.get("/api/vision-profiles", headers=headers)).json() == []

    async def test_cross_user_is_404(self, client, user_factory, prompt_factory):
        uid_a, headers_a = await user_factory()
        uid_b, headers_b = await user_factory()
        prompt_a = await prompt_factory(uid_a)
        created = (
            await client.post(
                "/api/vision-profiles", json=profile_payload(prompt_a.id), headers=headers_a
            )
        ).json()
        for method in ("get", "put", "delete"):
            if method == "get":
                resp = await client.get(f"/api/vision-profiles/{created['id']}", headers=headers_b)
            elif method == "put":
                resp = await client.put(
                    f"/api/vision-profiles/{created['id']}",
                    json=profile_payload(prompt_a.id),
                    headers=headers_b,
                )
            else:
                resp = await client.delete(
                    f"/api/vision-profiles/{created['id']}", headers=headers_b
                )
            assert resp.status_code == 404

    async def test_requires_auth(self, client):
        resp = await client.get("/api/vision-profiles")
        assert resp.status_code == 401

    async def test_foreign_system_prompt_rejected(self, client, user_factory, prompt_factory):
        """Creating a profile referencing another user's prompt must fail (ownership)."""
        uid_a, headers_a = await user_factory()
        uid_b, headers_b = await user_factory()
        prompt_a = await prompt_factory(uid_a)  # belongs to A
        resp = await client.post(
            "/api/vision-profiles", json=profile_payload(prompt_a.id), headers=headers_b
        )
        assert resp.status_code in (404, 422)


class TestActivation:
    async def test_activate_sets_exactly_one_active(
        self, client, user_factory, prompt_factory, db_session
    ):
        uid, headers = await user_factory()
        p1 = await prompt_factory(uid)
        p2 = await prompt_factory(uid)
        first = (
            await client.post("/api/vision-profiles", json=profile_payload(p1.id), headers=headers)
        ).json()
        second = (
            await client.post("/api/vision-profiles", json=profile_payload(p2.id), headers=headers)
        ).json()

        resp = await client.post(f"/api/vision-profiles/{first['id']}/activate", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

        listing = (await client.get("/api/vision-profiles", headers=headers)).json()
        active = [p for p in listing if p["is_active"]]
        assert len(active) == 1
        assert active[0]["id"] == first["id"]

        # activate the second → first deactivates
        await client.post(f"/api/vision-profiles/{second['id']}/activate", headers=headers)
        listing = (await client.get("/api/vision-profiles", headers=headers)).json()
        active = [p for p in listing if p["is_active"]]
        assert len(active) == 1
        assert active[0]["id"] == second["id"]

    async def test_concurrent_activation_always_one_active(
        self, client, user_factory, prompt_factory, db_session
    ):
        uid, headers = await user_factory()
        prompts = [await prompt_factory(uid) for _ in range(3)]
        created = []
        for p in prompts:
            body = (
                await client.post(
                    "/api/vision-profiles", json=profile_payload(p.id), headers=headers
                )
            ).json()
            created.append(body["id"])

        results = await asyncio.gather(
            *[
                client.post(f"/api/vision-profiles/{pid}/activate", headers=headers)
                for pid in created
            ],
            return_exceptions=True,
        )
        ok = [r for r in results if not isinstance(r, Exception) and r.status_code == 200]
        assert len(ok) >= 1

        factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
        async with factory() as s:
            count = (
                await s.execute(
                    select(func.count()).where(
                        models.VisionProfile.user_id == uid,
                        models.VisionProfile.is_active.is_(True),
                    )
                )
            ).scalar_one()
        assert count == 1

    async def test_activate_foreign_profile_404(self, client, user_factory, prompt_factory):
        uid_a, headers_a = await user_factory()
        _, headers_b = await user_factory()
        prompt_a = await prompt_factory(uid_a)
        created = (
            await client.post(
                "/api/vision-profiles", json=profile_payload(prompt_a.id), headers=headers_a
            )
        ).json()
        resp = await client.post(
            f"/api/vision-profiles/{created['id']}/activate", headers=headers_b
        )
        assert resp.status_code == 404
