---
name: backend-vision-service
status: done
depends_on: [[db-schema], [api-system-prompts], [api-vision-profiles], [services-image-validator], [services-limiters]]
implements: Architecture §16/§18/§19, Decision #10
related_files: backend/app/services/vision_service.py, backend/app/repositories/settings.py, backend/app/api/settings.py, backend/app/db/models.py (AppSettings), backend/tests/test_vision_service.py, backend/tests/test_settings.py, backend/app/db/migrations/versions/4884015c3395_app_settings.py
---

## What this is
VisionService: the single seam orchestrating rate/concurrency limits, image validation, active-profile + system-prompt + extra-instructions resolution, Fernet decryption, LangChain ChatOpenAI call (timeout=60, max_retries=0), and provider error translation to the exact stable strings of Decision #10 §14. Plus app_settings singleton storage for Universal Extra Instructions (+ GET/PUT /api/settings/extra-instructions).

## Current state
Complete. 13 VisionService tests (composition describe/ocr, auth+model forwarding, 6 status mappings, empty-response, no-active-profile, rate-limit-before-provider) + 4 settings tests + migration 4884015c3395.

## Key decisions made while building this
- Extra Instructions = `app_settings(key,value)` singleton row (see decisions.md + questions.md Q2).
- `_CachedSessionFactory` pattern for loop-lazy engine creation (same rationale as mcp_auth: asyncpg binds connections to the creating loop).
- `build_messages()` is a pure function; OCR never receives extra instructions — enforced by branch, not a flag (Decision #10 §4).
- A fresh `httpx.AsyncClient()` per provider call: the openai SDK (v3, vendors httpx2) otherwise caches a global client per event loop; a stale loop's transport throws `RuntimeError ... handler is closed` → APIConnectionError after server restarts (caught in e2e tests). One-shot clients are correct at this scale.
- RateLimitError/ConcurrencyLimitError wrapped into VisionServiceError with the same stable text so MCP callers see one exception type.
- Error translation order matters: APITimeoutError checked BEFORE APIConnectionError (subclass).
- `app.api.settings` module imported as `settings_routes` in main.py to avoid colliding with `app.config.settings`.

## Known gaps / TODO
- None for v1.
