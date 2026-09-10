"""Image validation tests (Decision #4, Architecture §17/§26):
valid JPEG/PNG/WebP pass; invalid base64, >5MB, corrupt bytes, disguised format
(GIF bytes), >8.3MP rejected — with stable error messages."""

import base64
import io

import pytest
from PIL import Image

from app.services.image_validator import (
    ImageValidationError,
    ImageValidator,
)


def _png_bytes(w: int = 10, h: int = 10, color: tuple = (255, 0, 0)) -> bytes:
    img = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(w: int = 10, h: int = 10) -> bytes:
    img = Image.new("RGB", (w, h), (0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _webp_bytes(w: int = 10, h: int = 10) -> bytes:
    img = Image.new("RGB", (w, h), (0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()


def _gif_bytes() -> bytes:
    img = Image.new("P", (10, 10))
    buf = io.BytesIO()
    img.save(buf, format="GIF")
    return buf.getvalue()


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


class TestValid:
    @pytest.mark.parametrize("maker", [_png_bytes, _jpeg_bytes, _webp_bytes])
    async def test_valid_formats_pass(self, maker):
        validator = ImageValidator()
        validated = validator.validate(_b64(maker()))
        assert validated.raw_bytes  # decoded image bytes
        assert validated.mime_type in ("image/png", "image/jpeg", "image/webp")

    async def test_pixels_within_8_3mp_pass(self):
        # 4000x2000 = 8.0 MP ≤ 8.3 MP → accept (panoramic, per Decision #4 table)
        validator = ImageValidator()
        # build a tiny-but-wide PNG by hand? Pillow can create it:
        img = Image.new("RGB", (4000, 2000))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        # compress well under 5MB trivially
        validator.validate(_b64(buf.getvalue()))


class TestRejected:
    async def test_invalid_base64(self):
        validator = ImageValidator()
        with pytest.raises(ImageValidationError) as exc_info:
            validator.validate("not-valid-base64!!!")
        assert "invalid" in str(exc_info.value).lower()

    async def test_over_5mb_rejected(self):
        validator = ImageValidator()
        # a PNG > 5MB (random noise, incompressible)
        import random

        random.seed(42)
        noise = Image.frombytes(
            "RGB", (1400, 1400), bytes(random.getrandbits(8) for _ in range(1400 * 1400 * 3))
        )
        buf = io.BytesIO()
        noise.save(buf, format="PNG")
        assert len(buf.getvalue()) > 5 * 1024 * 1024  # precondition
        with pytest.raises(ImageValidationError) as exc_info:
            validator.validate(_b64(buf.getvalue()))
        assert "size" in str(exc_info.value).lower()

    async def test_corrupt_bytes_rejected(self):
        validator = ImageValidator()
        png = bytearray(_png_bytes())
        png[50:100] = b"\x00" * 50  # corrupt the IDAT
        with pytest.raises(ImageValidationError):
            validator.validate(_b64(bytes(png)))

    async def test_disguised_gif_rejected(self):
        """GIF bytes declared as image/png must be rejected by signature check."""
        validator = ImageValidator()
        with pytest.raises(ImageValidationError) as exc_info:
            validator.validate(_b64(_gif_bytes()))
        assert (
            "unsupported" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()
        )

    async def test_over_8_3mp_rejected(self):
        """A highly-compressed image below 5MB but above 8.3MP must be rejected."""
        validator = ImageValidator()
        img = Image.new("RGB", (4000, 2200))  # 8.8 MP, solid color → tiny PNG
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        assert len(buf.getvalue()) < 5 * 1024 * 1024  # under size cap
        with pytest.raises(ImageValidationError) as exc_info:
            validator.validate(_b64(buf.getvalue()))
        assert "resolution" in str(exc_info.value).lower()

    async def test_truncated_data_rejected(self):
        validator = ImageValidator()
        png = _png_bytes()[:30]  # header only, no frames
        with pytest.raises(ImageValidationError):
            validator.validate(_b64(png))
