"""End-to-end MCP tool execution tests (Phase 11 + Architecture §26):
describe_image / ocr_image called through the real mounted /mcp endpoint with
the official MCP client; provider is a mock OpenAI-compatible server.
Verifies: auth context, mode-specific prompt composition, stable errors surface
as MCP tool errors."""

import asyncio
import base64
import io
import threading
import uuid

import httpx
import pytest
from argon2 import PasswordHasher
from PIL import Image
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.crypto import encrypt_api_key, generate_mcp_key, hash_mcp_key
from app.db import models
from app.db import session as db_session_mod
from app.main import create_app

PROVIDER_PORT = 48765


def _png_b64() -> str:
    img = Image.new("RGB", (8, 8), (150, 40, 40))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class MockProviderServer:
    """Real HTTP OpenAI-compatible mock so the backend's provider calls traverse
    the full network stack."""

    def __init__(self):
        import uvicorn
        from fastapi import FastAPI, Request

        self.app = FastAPI()
        self.requests: list[dict] = []
        self.respond_content = "A red square."
        self.respond_status = 200

        @self.app.post("/v1/chat/completions")
        async def chat(request: Request):
            body = await request.json()
            self.requests.append(
                {
                    "auth": request.headers.get("authorization"),
                    "model": body.get("model"),
                    "messages": body.get("messages"),
                }
            )
            if self.respond_status != 200:
                return httpx.Response(
                    self.respond_status,
                    json={"error": {"message": "boom", "type": "x"}},
                )
            return {
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "created": 0,
                "model": body.get("model"),
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": self.respond_content}}
                ],
            }

        self.config = uvicorn.Config(
            self.app, host="127.0.0.1", port=PROVIDER_PORT, log_level="error"
        )
        self.server = uvicorn.Server(self.config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self) -> None:
        self.thread.start()
        while not self.server.started:
            time_sleep(0.02)

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)


def time_sleep(t: float) -> None:
    import time

    time.sleep(t)


@pytest.fixture(scope="module")
def provider() -> MockProviderServer:
    srv = MockProviderServer()
    srv.start()
    yield srv
    srv.stop()


@pytest.fixture
async def e2e_app(db_engine, migrated_db, provider):
    """Backend app on a real port, profile pointing at the mock provider."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as s:
            yield s

    class ServerLoopFactory:
        def __init__(self, url):
            self.url = url
            self._factory = None

        def __call__(self):
            from sqlalchemy.ext.asyncio import create_async_engine

            if self._factory is None:
                engine = create_async_engine(self.url)
                self._factory = async_sessionmaker(engine, expire_on_commit=False)
            return self._factory

    import uvicorn

    test_app = create_app(mcp_session_factory_fn=ServerLoopFactory(migrated_db))
    test_app.dependency_overrides[db_session_mod.get_db] = override_get_db

    config = uvicorn.Config(test_app, host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        await asyncio.sleep(0.05)
    port = server.servers[0].sockets[0].getsockname()[1]

    yield {
        "base_url": f"http://127.0.0.1:{port}",
        "db_url": migrated_db,
        "provider": provider,
    }

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
async def mcp_user(db_engine, db_session, e2e_app):
    """User + MCP key + active profile at the mock provider."""
    user = models.User(
        email=f"e2e{uuid.uuid4().hex[:10]}@example.com",
        password_hash=PasswordHasher().hash("pw-123456"),
    )
    db_session.add(user)
    await db_session.flush()

    prompt = models.SystemPrompt(
        user_id=user.id, title="E2E prompt", content="You are the e2e vision model."
    )
    db_session.add(prompt)
    await db_session.flush()

    profile = models.VisionProfile(
        user_id=user.id,
        name="E2E Profile",
        endpoint=f"http://127.0.0.1:{PROVIDER_PORT}/v1",
        model="e2e-vision-model",
        system_prompt_id=prompt.id,
        encrypted_api_key=encrypt_api_key("sk-e2e-key"),
        is_active=True,
    )
    db_session.add(profile)

    key = generate_mcp_key()
    cred = models.McpCredential(user_id=user.id, key_hash=hash_mcp_key(key))
    db_session.add(cred)
    await db_session.commit()

    return {"user_id": user.id, "mcp_key": key}


async def _call_tool(base_url: str, key: str, tool: str, prompt: str):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with streamable_http_client(
        base_url + "/mcp",
        http_client=httpx.AsyncClient(headers={"Authorization": f"Bearer {key}"}),
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await session.call_tool(
                tool,
                {
                    "image": {"type": "image", "data": _png_b64(), "mimeType": "image/png"},
                    "prompt": prompt,
                },
            )


class TestToolExecution:
    async def test_describe_image_roundtrip(self, e2e_app, mcp_user, provider):
        result = await _call_tool(
            e2e_app["base_url"], mcp_user["mcp_key"], "describe_image", "What is this?"
        )
        text = result.content[0].text if result.content else ""
        assert "A red square." in text

        req = provider.requests[-1]
        assert req["auth"] == "Bearer sk-e2e-key"
        assert req["model"] == "e2e-vision-model"
        msgs = req["messages"]
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "You are the e2e vision model."
        image_part = next(p for p in msgs[1]["content"] if p["type"] == "image_url")
        assert image_part["image_url"]["url"].startswith("data:image/png;base64,")

    async def test_ocr_image_roundtrip(self, e2e_app, mcp_user, provider):
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from app.repositories.settings import AppSettingsRepository

        engine = create_async_engine(e2e_app["db_url"])
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as s:
            await AppSettingsRepository(s).set_extra_instructions("DESCRIBE-ONLY-MARKER")

        result = await _call_tool(
            e2e_app["base_url"], mcp_user["mcp_key"], "ocr_image", "Extract all text."
        )
        assert not result.is_error
        req = provider.requests[-1]
        text_part = next(p for p in req["messages"][1]["content"] if p["type"] == "text")
        assert "DESCRIBE-ONLY-MARKER" not in text_part["text"]
        assert "Extract all text." in text_part["text"]

    async def test_no_active_profile_returns_stable_error(
        self, e2e_app, mcp_user, provider, db_session
    ):
        from sqlalchemy import update

        await db_session.execute(update(models.VisionProfile).values(is_active=False))
        await db_session.commit()

        result = await _call_tool(
            e2e_app["base_url"], mcp_user["mcp_key"], "describe_image", "What is this?"
        )
        assert result.is_error
        assert "No active Vision Profile is configured" in result.content[0].text

        # reactivate for other tests
        await db_session.execute(update(models.VisionProfile).values(is_active=True))
        await db_session.commit()
