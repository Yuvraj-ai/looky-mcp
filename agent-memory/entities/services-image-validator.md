---
name: services-image-validator
status: done
depends_on: []
implements: Decision #4, Architecture §17
related_files: backend/app/services/image_validator.py, backend/tests/test_image_validator.py
---

## What this is
Pillow-based validation: base64 → 5MB → signature-sniffed format (JPEG/PNG/WebP) → full decode → 8.3MP. No modification of image bytes.

## Current state
Complete. 10 tests (valid formats, 8.0MP panoramic accept, invalid base64, >5MB, corrupt, disguised GIF, >8.3MP-under-5MB, truncated).

## Key decisions made while building this
- Corrupt/truncated bytes surface as PIL `OSError`/`UnidentifiedImageError` — caught and mapped to stable "Image data is invalid" (mypy-narrowed format via local `fmt` var + assert).
- `base64.b64decode(validate=True)` rejects embedded garbage (Decision #4 "validate base64").

## Known gaps / TODO
- None.
