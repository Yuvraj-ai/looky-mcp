"""Real-provider e2e (opt-in): runs only when VISION_E2E_BASE_URL, VISION_E2E_API_KEY
and VISION_E2E_MODEL are set. Exercises the full stack against a genuine
OpenAI-compatible vision endpoint. See questions.md Q3."""

import base64
import io
import os
import uuid

import pytest
from PIL import Image

BASE_URL = os.environ.get("VISION_E2E_BASE_URL")
API_KEY = os.environ.get("VISION_E2E_API_KEY")
MODEL = os.environ.get("VISION_E2E_MODEL")

pytestmark = pytest.mark.skipif(
    not (BASE_URL and API_KEY and MODEL),
    reason="set VISION_E2E_BASE_URL, VISION_E2E_API_KEY, VISION_E2E_MODEL to run",
)


def _png_b64() -> str:
    img = Image.new("RGB", (120, 60), (30, 30, 200))
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    draw.text((10, 20), "HELLO 42", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


async def test_real_provider_describe_and_ocr(db_engine, migrated_db, db_session):
    """Full stack: DB → VisionService → real provider → text answer."""
    from mcp.types import ImageContent
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.crypto import encrypt_api_key
    from app.db import models
    from app.services.vision_service import VisionService

    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as s:
        user = models.User(email=f"real{uuid.uuid4().hex[:8]}@example.com")
        s.add(user)
        await s.flush()
        prompt = models.SystemPrompt(
            user_id=user.id, title="t", content="You describe images briefly."
        )
        s.add(prompt)
        await s.flush()
        profile = models.VisionProfile(
            user_id=user.id,
            name="real",
            endpoint=BASE_URL,
            model=MODEL,
            system_prompt_id=prompt.id,
            encrypted_api_key=encrypt_api_key(API_KEY),
            is_active=True,
        )
        s.add(profile)
        await s.commit()
        uid = user.id

    service = VisionService(session_factory_fn=lambda: factory)
    image = ImageContent(type="image", data=_png_b64(), mimeType="image/png")

    described = await service.run(
        user_id=uid,
        mode="describe",
        image=image,
        prompt="What text is in this image? Answer with just the text.",
    )
    assert "42" in described.upper()

    ocr_result = await service.run(
        user_id=uid, mode="ocr", image=image, prompt="Extract the text exactly."
    )
    assert "42" in ocr_result.upper()
