"""VisionService tests (Decision #10, Architecture §16/§26): message composition
per mode, error translation to stable strings, rate/concurrency integration.

The vision LLM is a mock OpenAI-compatible server (httpx MockTransport-style,
via langchain's configurable http client) — no real provider needed.
"""

import base64
import io
import uuid

import httpx
import pytest
from argon2 import PasswordHasher
from PIL import Image
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import models


@pytest.fixture
def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


def _png_b64(w: int = 8, h: int = 8) -> str:
    img = Image.new("RGB", (w, h), (200, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
async def user_with_profile(db_session):
    """User + system prompt + active vision profile (mock endpoint)."""
    from app.crypto import encrypt_api_key

    user = models.User(
        email=f"vs{uuid.uuid4().hex[:10]}@example.com",
        password_hash=PasswordHasher().hash("pw-123456"),
    )
    db_session.add(user)
    await db_session.flush()

    prompt = models.SystemPrompt(
        user_id=user.id, title="Vision prompt", content="You analyze images."
    )
    db_session.add(prompt)
    await db_session.flush()

    profile = models.VisionProfile(
        user_id=user.id,
        name="Mock Profile",
        endpoint="https://mock.provider.test/v1",
        model="mock-vision-model",
        system_prompt_id=prompt.id,
        encrypted_api_key=encrypt_api_key("sk-mock-key"),
        is_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    return user, prompt, profile


class FakeProvider:
    """Configurable OpenAI-compatible responder built on httpx.MockTransport."""

    def __init__(self, response_content="The image shows a red square.", status=200):
        self.requests: list[dict] = []
        self.response_content = response_content
        self.status = status

    def handler(self, request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.content.decode())
        self.requests.append(
            {
                "url": str(request.url),
                "auth": request.headers.get("authorization"),
                "body": body,
            }
        )
        if self.status != 200:
            err_body = {"error": {"message": "provider error", "type": "invalid_request_error"}}
            return httpx.Response(self.status, json=err_body)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": 0,
                "model": body.get("model"),
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": self.response_content}}
                ],
            },
        )

    def transport(self) -> httpx.AsyncHTTPTransport:
        return httpx.MockTransport(self.handler)


def _make_service(provider_status_map: dict[str, tuple]) -> "object":
    """Build a VisionService whose ChatOpenAI calls route to FakeProvider via
    a per-endpoint transport patch."""
    import app.services.vision_service as vs

    return vs


class TestMessageComposition:
    async def test_describe_includes_extra_instructions(
        self, db_session, session_factory, user_with_profile
    ):
        from app.repositories.settings import AppSettingsRepository
        from app.services.vision_service import VisionService

        user, prompt, profile = user_with_profile
        await AppSettingsRepository(db_session).set_extra_instructions(
            "Always answer in bullet points."
        )

        provider = FakeProvider()
        service = VisionService(
            http_transport=provider.transport(), session_factory_fn=lambda: session_factory
        )

        image_content = _build_image_content()
        result = await service.run(
            user_id=user.id, mode="describe", image=image_content, prompt="What is this?"
        )
        assert result == "The image shows a red square."

        req = provider.requests[0]
        msgs = req["body"]["messages"]
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "You analyze images."
        user_msg = msgs[1]
        text_part = next(p for p in user_msg["content"] if p["type"] == "text")
        assert "Always answer in bullet points." in text_part["text"]
        assert "What is this?" in text_part["text"]
        img_part = next(p for p in user_msg["content"] if p["type"] == "image_url")
        assert img_part["image_url"]["url"].startswith("data:image/png;base64,")

    async def test_ocr_excludes_extra_instructions(
        self, db_session, session_factory, user_with_profile
    ):
        from app.repositories.settings import AppSettingsRepository
        from app.services.vision_service import VisionService

        user, prompt, profile = user_with_profile
        await AppSettingsRepository(db_session).set_extra_instructions("NEVER-IN-OCR-MARKER")

        provider = FakeProvider(response_content="KeyError: 'username'")
        service = VisionService(
            http_transport=provider.transport(), session_factory_fn=lambda: session_factory
        )

        result = await service.run(
            user_id=user.id,
            mode="ocr",
            image=_build_image_content(),
            prompt="Extract the error message.",
        )
        assert result == "KeyError: 'username'"

        req = provider.requests[0]
        msgs = req["body"]["messages"]
        text_part = next(p for p in msgs[1]["content"] if p["type"] == "text")
        assert "NEVER-IN-OCR-MARKER" not in text_part["text"]
        assert "Extract the error message." in text_part["text"]

    async def test_provider_auth_and_model_forwarded(
        self, db_session, session_factory, user_with_profile
    ):
        from app.services.vision_service import VisionService

        user, prompt, profile = user_with_profile
        provider = FakeProvider()
        service = VisionService(
            http_transport=provider.transport(), session_factory_fn=lambda: session_factory
        )
        await service.run(
            user_id=user.id, mode="describe", image=_build_image_content(), prompt="p"
        )
        req = provider.requests[0]
        assert req["auth"] == "Bearer sk-mock-key"
        assert req["body"]["model"] == "mock-vision-model"
        assert "/chat/completions" in req["url"]


class TestErrorTranslation:
    async def test_no_active_profile(self, db_session, session_factory, user_with_profile):
        from app.services.vision_service import VisionService, VisionServiceError

        user, prompt, profile = user_with_profile
        profile.is_active = False
        await db_session.commit()

        service = VisionService(session_factory_fn=lambda: session_factory)
        with pytest.raises(VisionServiceError) as exc:
            await service.run(
                user_id=user.id, mode="describe", image=_build_image_content(), prompt="p"
            )
        assert str(exc.value) == "No active Vision Profile is configured"

    @pytest.mark.parametrize(
        "status,expected",
        [
            (401, "Vision Profile authentication failed"),
            (400, "Vision request rejected"),
            (404, "Vision Profile configuration is invalid"),
            (429, "Vision service rate limit reached"),
            (500, "Vision service temporarily unavailable"),
            (503, "Vision service temporarily unavailable"),
        ],
    )
    async def test_provider_status_mapping(
        self, db_session, session_factory, user_with_profile, status, expected
    ):
        from app.services.vision_service import VisionService, VisionServiceError

        user, _, _ = user_with_profile
        provider = FakeProvider(status=status)
        service = VisionService(
            http_transport=provider.transport(), session_factory_fn=lambda: session_factory
        )
        with pytest.raises(VisionServiceError) as exc:
            await service.run(
                user_id=user.id, mode="describe", image=_build_image_content(), prompt="p"
            )
        assert str(exc.value) == expected

    async def test_invalid_image_rejected_before_provider_call(
        self, db_session, session_factory, user_with_profile
    ):
        from mcp.types import ImageContent

        from app.services.image_validator import ImageValidationError
        from app.services.vision_service import VisionService

        user, _, _ = user_with_profile
        provider = FakeProvider()
        service = VisionService(
            http_transport=provider.transport(), session_factory_fn=lambda: session_factory
        )

        bad = ImageContent(type="image", data="not-base64!!", mimeType="image/png")
        with pytest.raises(ImageValidationError):
            await service.run(user_id=user.id, mode="describe", image=bad, prompt="p")
        assert provider.requests == []  # provider never contacted

    async def test_empty_response_maps_to_invalid_response(
        self, db_session, session_factory, user_with_profile
    ):
        from app.services.vision_service import VisionService, VisionServiceError

        user, _, _ = user_with_profile
        provider = FakeProvider(response_content="")
        service = VisionService(
            http_transport=provider.transport(), session_factory_fn=lambda: session_factory
        )
        with pytest.raises(VisionServiceError) as exc:
            await service.run(
                user_id=user.id, mode="describe", image=_build_image_content(), prompt="p"
            )
        assert str(exc.value) == "Vision service returned invalid response"


class TestLimitsIntegration:
    async def test_rate_limit_before_provider(self, db_session, session_factory, user_with_profile):
        from app.services.rate_limiter import RateLimiter
        from app.services.vision_service import VisionService, VisionServiceError

        user, _, _ = user_with_profile
        provider = FakeProvider()
        exhausted = RateLimiter(max_calls=1, window_seconds=60)
        service = VisionService(
            http_transport=provider.transport(),
            rate_limiter=exhausted,
            session_factory_fn=lambda: session_factory,
        )

        ok = await service.run(
            user_id=user.id, mode="describe", image=_build_image_content(), prompt="p"
        )
        assert ok == "The image shows a red square."
        with pytest.raises(VisionServiceError) as exc:
            await service.run(
                user_id=user.id, mode="describe", image=_build_image_content(), prompt="p"
            )
        assert str(exc.value) == "Vision call rate limit reached"
        assert len(provider.requests) == 1  # second call never reached provider


def _build_image_content():
    from mcp.types import ImageContent

    return ImageContent(type="image", data=_png_b64(), mimeType="image/png")
