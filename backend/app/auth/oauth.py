"""Google OAuth (Architecture §9, §28.2): authorization-code flow.
id_token verified against Google's JWKS: RS256 signature, audience, issuer,
expiry. Auto-link by verified email (Architecture §28.2 option (a)).
No public signup: unknown emails are rejected."""

import base64
import json
import secrets
import time

import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa as crypto_rsa
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import set_session_cookie
from app.config import settings
from app.db.session import get_db
from app.repositories.users import UserRepository

router = APIRouter(prefix="/api/auth/google", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")


async def _fetch_token(data: dict) -> dict:
    """Exchange authorization code for tokens (patched in tests)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data=data, timeout=10)
        resp.raise_for_status()
        return resp.json()


async def _fetch_jwks() -> dict:
    """Google's signing keys (patched in tests)."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(GOOGLE_JWKS_URL, timeout=10)
        resp.raise_for_status()
        return resp.json()


def _b64url_decode(seg: str) -> bytes:
    padding = "=" * (-len(seg) % 4)
    return base64.urlsafe_b64decode(seg + padding)


def _b64url_int(v: str) -> int:
    return int.from_bytes(_b64url_decode(v), "big")


async def verify_google_id_token(id_token: str, audience: str) -> dict:
    """Verify RS256 signature against JWKS, iss, aud, exp. Returns claims."""
    try:
        header_seg, payload_seg, sig_seg = id_token.split(".")
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid Google token") from exc

    header = json.loads(_b64url_decode(header_seg))
    if header.get("alg") != "RS256":
        raise HTTPException(status_code=401, detail="Invalid Google token")

    jwks = await _fetch_jwks()
    key = next((k for k in jwks["keys"] if k.get("kid") == header.get("kid")), None)
    if key is None:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    pub = crypto_rsa.RSAPublicNumbers(_b64url_int(key["e"]), _b64url_int(key["n"])).public_key()

    signing_input = f"{header_seg}.{payload_seg}".encode()
    signature = _b64url_decode(sig_seg)
    try:
        pub.verify(signature, signing_input, asym_padding.PKCS1v15(), hashes.SHA256())
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid Google token") from exc

    claims = json.loads(_b64url_decode(payload_seg))
    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    if claims.get("aud") != audience:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    if claims.get("exp", 0) < time.time():
        raise HTTPException(status_code=401, detail="Invalid Google token")
    return claims


def _redirect_uri() -> str:
    return f"{settings.PUBLIC_BASE_URL}/api/auth/google/callback"


@router.get("/start")
async def start() -> Response:
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(status_code=404, detail="Google login is not configured")
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": "openid email",
        "state": secrets.token_urlsafe(32),
    }
    query = "&".join(f"{k}={httpx.QueryParams({k: v}).get(k)}" for k, v in params.items())
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}")


@router.get("/callback")
async def callback(code: str = "", state: str = "", db: AsyncSession = Depends(get_db)) -> Response:
    if not code:
        raise HTTPException(status_code=401, detail="Google login failed")

    token_response = await _fetch_token(
        {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": _redirect_uri(),
        }
    )
    claims = await verify_google_id_token(
        token_response["id_token"], settings.GOOGLE_OAUTH_CLIENT_ID
    )

    if not claims.get("email_verified"):
        raise HTTPException(status_code=403, detail="Google email is not verified")

    repo = UserRepository(db)
    user = await repo.get_by_email(claims["email"])

    if user is not None and user.google_sub is None:
        # auto-link by verified email (Architecture §28.2 option (a))
        user.google_sub = claims["sub"]
        await db.commit()
    elif user is None:
        # no public signup (Architecture §9)
        raise HTTPException(
            status_code=403,
            detail="No account exists for this email. Ask an administrator to provision it.",
        )

    assert user is not None
    response = JSONResponse({"ok": True})
    set_session_cookie(response, user.id)
    return response
