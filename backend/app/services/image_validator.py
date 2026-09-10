"""Image validation (Decision #4, Architecture §17): base64 → 5MB cap →
signature-sniffed format (JPEG/PNG/WebP only) → full decode → 8.3MP cap.
No resizing/conversion — validated bytes are passed through unmodified."""

import base64
import binascii
import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

MAX_ENCODED_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 8_294_400  # ~8.3 MP (4K UHD class)
ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class ImageValidationError(Exception):
    """Stable, user-facing validation failure (Decision #5 message rules)."""


@dataclass
class ValidatedImage:
    raw_bytes: bytes
    mime_type: str
    width: int
    height: int


class ImageValidator:
    def validate(self, base64_data: str) -> ValidatedImage:
        raw_bytes = self._decode_base64(base64_data)
        self._check_size(raw_bytes)
        try:
            with Image.open(io.BytesIO(raw_bytes)) as img:
                self._check_format(img)
                img.load()  # force full decode — catches corrupt data
                self._check_resolution(img)
                fmt = img.format
                assert fmt is not None  # narrowed by _check_format above
                mime = ALLOWED_FORMATS[fmt]
                width, height = img.size
        except UnidentifiedImageError as exc:
            raise ImageValidationError("Image data is invalid") from exc
        except OSError as exc:  # broken/truncated data stream from the decoder
            raise ImageValidationError("Image data is invalid") from exc
        return ValidatedImage(raw_bytes=raw_bytes, mime_type=mime, width=width, height=height)

    def _decode_base64(self, data: str) -> bytes:
        try:
            return base64.b64decode(data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ImageValidationError("Image data is invalid") from exc

    def _check_size(self, raw_bytes: bytes) -> None:
        if len(raw_bytes) > MAX_ENCODED_BYTES:
            raise ImageValidationError("Image exceeds the size limit of 5 MB")

    def _check_format(self, img: Image.Image) -> None:
        if img.format not in ALLOWED_FORMATS:
            raise ImageValidationError(f"Image format is unsupported: {img.format or 'unknown'}")

    def _check_resolution(self, img: Image.Image) -> None:
        if img.width * img.height > MAX_PIXELS:
            raise ImageValidationError(
                "Image exceeds the maximum supported resolution of 8.3 megapixels"
            )
