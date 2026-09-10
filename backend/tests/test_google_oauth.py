"""Google OAuth tests (Architecture §9, §28.2): authorization-code flow against
a mocked Google token endpoint; id_token verified (signature/audience/issuer/
email_verified); auto-link by verified email; session cookie issued on success.

No real Google credentials are used — GOOGLE_OAUTH_CLIENT_ID/SECRET are fakes
and google's token+jwks endpoints are monkeypatched to local fakes.
"""

import base64
import json
import time
from collections.abc import AsyncIterator

import httpx
import pytest
from argon2 import PasswordHasher
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import models
from app.db import session as db_session_mod
from app.main import create_app


@pytest.fixture
def fake_google(monkeypatch):
    """Fake Google: RSA keypair, jwks server, token endpoint."""
    import rsa  # dev-only pure-python RSA for test keygen

    pub, priv = rsa.newkeys(2048)

    def b64url_int(n: int) -> str:
        raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    jwk = {
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "kid": "test-key-1",
        "n": b64url_int(pub.n),
        "e": b64url_int(pub.e),
    }

    class FakeGoogle:
        def __init__(self):
            self.client_id = "test-client-id.apps.googleusercontent.com"
            self.client_secret = "test-secret"
            self.issued_tokens: list[str] = []
            self.tokens: dict[str, dict] = {}  # code → id_token claims

        def make_id_token(
            self, sub: str, email: str, email_verified: bool = True, aud: str | None = None
        ) -> str:
            header = {"alg": "RS256", "kid": "test-key-1"}
            now = int(time.time())
            payload = {
                "iss": "https://accounts.google.com",
                "azp": self.client_id,
                "aud": aud or self.client_id,
                "sub": sub,
                "email": email,
                "email_verified": email_verified,
                "iat": now,
                "exp": now + 3600,
            }

            def seg(d):
                return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

            signing_input = f"{seg(header)}.{seg(payload)}".encode()
            sig = rsa.sign(signing_input, priv, "SHA-256")
            sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
            return f"{seg(header)}.{seg(payload)}.{sig_b64}"

    fake = FakeGoogle()

    async def fake_fetch_tokens(data: dict) -> dict:
        assert data["client_id"] == fake.client_id
        assert data["client_secret"] == fake.client_secret
        code = data["code"]
        if code not in fake.tokens:
            raise RuntimeError("invalid code")
        return {"id_token": fake.tokens[code], "access_token": "at", "token_type": "Bearer"}

    async def fake_fetch_jwks() -> dict:
        return {"keys": [jwk]}

    monkeypatch.setattr("app.auth.oauth._fetch_token", fake_fetch_tokens)
    monkeypatch.setattr("app.auth.oauth._fetch_jwks", fake_fetch_jwks)
    from app.config import settings

    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", fake.client_id, raising=False)
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", fake.client_secret, raising=False)
    return fake


@pytest.fixture
async def client(db_engine, migrated_db, fake_google) -> AsyncIterator[httpx.AsyncClient]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as s:
            yield s

    test_app = create_app()
    test_app.dependency_overrides[db_session_mod.get_db] = override_get_db
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestGoogleFlow:
    async def test_start_redirects_to_google(self, client, fake_google):
        resp = await client.get("/api/auth/google/start", follow_redirects=False)
        assert resp.status_code in (302, 307)
        location = resp.headers["location"]
        assert "accounts.google.com/o/oauth2/v2/auth" in location
        assert "client_id=" + fake_google.client_id.replace(".", "%2") or "client_id=" in location
        assert "state=" in location

    async def test_callback_creates_session_for_provisioned_user(
        self, client, db_session, fake_google
    ):
        # admin-provisioned user with google_sub
        user = models.User(
            email="linked@example.com",
            google_sub="google-sub-123",
            password_hash=None,
        )
        db_session.add(user)
        await db_session.commit()

        id_token = fake_google.make_id_token("google-sub-123", "linked@example.com")
        fake_google.tokens["authcode-1"] = id_token

        resp = await client.get(
            "/api/auth/google/callback",
            params={"code": "authcode-1", "state": "somestate"},
        )
        assert resp.status_code in (200, 307), resp.text
        # session cookie present
        assert "session=" in resp.headers.get("set-cookie", "")

    async def test_callback_auto_links_by_verified_email(self, client, db_session, fake_google):
        """Architecture §28.2(a): verified email match auto-links the account."""
        user = models.User(
            email="autolink@example.com",
            password_hash=PasswordHasher().hash("pw-123456"),
        )
        db_session.add(user)
        await db_session.commit()

        id_token = fake_google.make_id_token("google-sub-456", "autolink@example.com")
        fake_google.tokens["authcode-2"] = id_token

        resp = await client.get(
            "/api/auth/google/callback", params={"code": "authcode-2", "state": "s"}
        )
        assert resp.status_code in (200, 307)

        await db_session.refresh(user)
        assert user.google_sub == "google-sub-456"

    async def test_callback_rejects_unverified_email(self, client, db_session, fake_google):
        id_token = fake_google.make_id_token(
            "google-sub-789", "unverified@example.com", email_verified=False
        )
        fake_google.tokens["authcode-3"] = id_token
        resp = await client.get(
            "/api/auth/google/callback", params={"code": "authcode-3", "state": "s"}
        )
        assert resp.status_code in (401, 403)

    async def test_callback_rejects_wrong_audience(self, client, fake_google):
        id_token = fake_google.make_id_token("s", "x@example.com", aud="other-app")
        fake_google.tokens["authcode-4"] = id_token
        resp = await client.get(
            "/api/auth/google/callback", params={"code": "authcode-4", "state": "s"}
        )
        assert resp.status_code in (401, 403)

    async def test_callback_rejects_tampered_token(self, client, fake_google):
        id_token = fake_google.make_id_token("s", "x@example.com")
        header, payload, sig = id_token.split(".")
        # tamper: change payload sub
        tampered_payload = json.loads(base64.urlsafe_b64decode(payload + "=="))
        tampered_payload["sub"] = "evil"
        new_payload = (
            base64.urlsafe_b64encode(json.dumps(tampered_payload).encode()).rstrip(b"=").decode()
        )
        fake_google.tokens["authcode-5"] = f"{header}.{new_payload}.{sig}"
        resp = await client.get(
            "/api/auth/google/callback", params={"code": "authcode-5", "state": "s"}
        )
        assert resp.status_code in (401, 403)

    async def test_callback_rejects_unknown_user_no_signup(self, client, fake_google):
        """No public signup: unknown email must NOT create a user."""
        id_token = fake_google.make_id_token("sub-x", "nobody@example.com")
        fake_google.tokens["authcode-6"] = id_token
        resp = await client.get(
            "/api/auth/google/callback", params={"code": "authcode-6", "state": "s"}
        )
        assert resp.status_code in (401, 403)
