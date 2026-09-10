"""Signed-cookie sessions — Architecture §9 NEW (Implementation Detail).

itsdangerous-signed user UUID, HttpOnly + Secure + SameSite=Lax cookie,
7-day sliding expiry. No session table (revocation-on-demand deferred).
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

from fastapi import Depends, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

COOKIE_NAME = "session"
MAX_AGE_SECONDS = 7 * 24 * 3600

_serializer: URLSafeTimedSerializer | None = None


def _get_serializer() -> URLSafeTimedSerializer:
    global _serializer
    if _serializer is None:
        _serializer = URLSafeTimedSerializer(settings.APP_SECRET_KEY)
    return _serializer


def sign_session(user_id: uuid.UUID) -> str:
    return _get_serializer().dumps(str(user_id))


def read_session(token: str | None) -> uuid.UUID | None:
    if not token:
        return None
    try:
        value = _get_serializer().loads(token, max_age=MAX_AGE_SECONDS)
        return uuid.UUID(value)
    except (BadSignature, SignatureExpired, ValueError):
        return None


def set_session_cookie(response: Response, user_id: uuid.UUID) -> None:
    # Secure cookie for HTTPS deployments; relaxed for plain-http local dev only
    # (PUBLIC_BASE_URL set to http://...).
    response.set_cookie(
        key=COOKIE_NAME,
        value=sign_session(user_id),
        max_age=MAX_AGE_SECONDS,
        httponly=True,
        secure=not settings.PUBLIC_BASE_URL.startswith("http://"),
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


async def get_current_user_id(
    request: Request,
) -> AsyncIterator[uuid.UUID]:
    """FastAPI dependency: resolve session cookie to user UUID or 401."""
    from fastapi import HTTPException

    user_id = read_session(request.cookies.get(COOKIE_NAME))
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    yield user_id


CurrentUser = Depends(get_current_user_id)


def session_expiry_now() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=MAX_AGE_SECONDS)
