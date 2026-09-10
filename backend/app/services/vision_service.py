"""VisionService (Architecture §16, Decision #10): the single seam between MCP
tool handlers and everything else — limits, validation, profile/prompt resolution,
decryption, message composition, provider call, error translation.

The REST API never calls this; it only manages the data VisionService reads."""

import uuid
from collections.abc import Callable

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from mcp.types import ImageContent
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.crypto import decrypt_api_key
from app.repositories.settings import AppSettingsRepository
from app.repositories.system_prompts import SystemPromptRepository
from app.repositories.vision_profiles import VisionProfileRepository
from app.services.concurrency_limiter import (
    ConcurrencyLimitError,
    run_with_concurrency_limit,
)
from app.services.image_validator import ImageValidationError, ImageValidator
from app.services.rate_limiter import RateLimiter, RateLimitError


class _CachedSessionFactory:
    """Engine created lazily inside the serving loop (uvicorn's), cached per
    process — avoids cross-loop asyncpg usage; see backend-mcp-server entity."""

    def __init__(self):
        self._factory: async_sessionmaker[AsyncSession] | None = None

    def __call__(self) -> async_sessionmaker[AsyncSession]:
        if self._factory is None:
            from app.db.session import build_session_factory

            self._factory = build_session_factory()
        return self._factory


class VisionServiceError(Exception):
    """Stable application-level error (Decision #10 §14 table). Messages are
    exact strings — do not paraphrase."""


_ERROR_BY_STATUS = {
    401: "Vision Profile authentication failed",
    400: "Vision request rejected",
    404: "Vision Profile configuration is invalid",
    429: "Vision service rate limit reached",
}


class VisionService:
    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        http_transport: httpx.AsyncBaseTransport | None = None,
        session_factory_fn: Callable[[], async_sessionmaker[AsyncSession]] | None = None,
    ):
        # shared per-process limiter (in-memory, Decision #9)
        self._rate_limiter = rate_limiter
        self._http_transport = http_transport  # tests inject MockTransport
        self._session_factory_fn = session_factory_fn or _CachedSessionFactory()

    async def run(self, *, user_id: uuid.UUID, mode: str, image: ImageContent, prompt: str) -> str:
        """mode: "describe" | "ocr" — set by tool identity, never an LLM flag."""
        if self._rate_limiter is None:
            from app.services import rate_limiter as rl

            self._rate_limiter = rl.get_default_limiter()
        try:
            await self._rate_limiter.check(user_id)
        except RateLimitError as exc:
            raise VisionServiceError("Vision call rate limit reached") from exc

        try:
            return await run_with_concurrency_limit(
                user_id, lambda: self._execute(user_id, mode, image, prompt)
            )
        except ConcurrencyLimitError as exc:
            raise VisionServiceError("Too many concurrent vision calls") from exc

    async def _execute(
        self, user_id: uuid.UUID, mode: str, image: ImageContent, prompt: str
    ) -> str:
        try:
            validated = ImageValidator().validate(image.data)
        except ImageValidationError:
            raise  # already a stable message

        factory = self._session_factory_fn()
        async with factory() as session:
            vrepo = VisionProfileRepository(session)
            profile = await vrepo.get_active(user_id)
            if profile is None:
                raise VisionServiceError("No active Vision Profile is configured")

            sprompt = await SystemPromptRepository(session).get_for_user(
                profile.system_prompt_id, user_id
            )
            if sprompt is None:
                raise VisionServiceError("No active Vision Profile is configured")

            extra = await AppSettingsRepository(session).get_extra_instructions()

        api_key = decrypt_api_key(profile.encrypted_api_key)

        try:
            answer = await self._call_provider(
                endpoint=profile.endpoint,
                model=profile.model,
                api_key=api_key,
                mode=mode,
                system_prompt=sprompt.content,
                extra_instructions=extra if mode == "describe" else "",
                user_prompt=prompt,
                image=validated,
            )
        except VisionServiceError:
            raise
        except (
            RateLimitError,  # pragma: no cover — checked before the call
            ConcurrencyLimitError,
        ):  # pragma: no cover
            raise
        except Exception as exc:
            raise self._translate(exc) from exc

        if not answer.strip():
            raise VisionServiceError("Vision service returned invalid response")
        return answer

    # --- provider interaction ---

    async def _call_provider(
        self,
        *,
        endpoint: str,
        model: str,
        api_key: str,
        mode: str,
        system_prompt: str,
        extra_instructions: str,
        user_prompt: str,
        image,  # ValidatedImage
    ) -> str:
        from langchain_openai import ChatOpenAI

        kwargs: dict = {}
        if self._http_transport is not None:
            kwargs["http_async_client"] = httpx.AsyncClient(transport=self._http_transport)
        else:
            # fresh client per call: the openai SDK otherwise caches a global
            # httpx client per event loop, and a stale loop's transport breaks
            # after the server restarts (tests) — one-shot clients are also
            # correct for single-use calls at this scale
            kwargs["http_async_client"] = httpx.AsyncClient()

        client = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=endpoint,
            timeout=60,  # Decision #10: locked 60s
            max_retries=0,  # Decision #10: zero automatic retries
            **kwargs,
        )

        messages = build_messages(
            mode=mode,
            system_prompt=system_prompt,
            extra_instructions=extra_instructions,
            user_prompt=user_prompt,
            image=image,
        )
        response = await client.ainvoke(messages)
        content = response.content
        if not isinstance(content, str):
            content = str(content)
        return content

    # --- error translation (Decision #10 §14) ---

    def _translate(self, exc: Exception) -> VisionServiceError:
        import openai

        if isinstance(exc, openai.AuthenticationError):
            return VisionServiceError("Vision Profile authentication failed")
        if isinstance(exc, openai.RateLimitError):
            return VisionServiceError("Vision service rate limit reached")
        if isinstance(exc, openai.APITimeoutError):
            return VisionServiceError("Vision request timed out")
        if isinstance(exc, openai.APIConnectionError):
            return VisionServiceError("Vision service unavailable")
        if isinstance(exc, openai.APIStatusError):
            mapped = _ERROR_BY_STATUS.get(exc.status_code)
            if mapped is None and 500 <= exc.status_code < 600:
                mapped = "Vision service temporarily unavailable"
            return VisionServiceError(mapped or "Vision service returned invalid response")
        return VisionServiceError("Vision service returned invalid response")


def build_messages(
    *,
    mode: str,
    system_prompt: str,
    extra_instructions: str,
    user_prompt: str,
    image,  # ValidatedImage
) -> list:
    """Decision #10 §4 composition:
    describe = System + ExtraInstructions + UserPrompt + Image
    ocr      = System + UserPrompt + Image  (extra NEVER included — enforced here)"""
    system = SystemMessage(content=system_prompt)

    if mode == "describe" and extra_instructions:
        text = f"{extra_instructions}\n{user_prompt}"
    else:
        text = user_prompt

    human = HumanMessage(
        content=[
            {"type": "text", "text": text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image.mime_type};base64,{_b64(image.raw_bytes)}"},
            },
        ]
    )
    return [system, human]


def _b64(raw: bytes) -> str:
    import base64

    return base64.b64encode(raw).decode()
