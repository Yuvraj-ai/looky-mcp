"""Async engine/session management (Architecture §21 db/session.py)."""

from collections.abc import AsyncGenerator
import ssl

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_asyncpg_clean_url_and_args(url_str: str) -> tuple[str, dict]:
    url = make_url(url_str)
    query = dict(url.query)
    needs_ssl = "ssl" in query or "sslmode" in query
    query.pop("sslmode", None)
    query.pop("ssl", None)
    clean_url = url.set(query=query).render_as_string(hide_password=False)

    connect_args = {}
    if needs_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx

    return clean_url, connect_args


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        clean_url, connect_args = _get_asyncpg_clean_url_and_args(settings.DATABASE_URL)
        _engine = create_async_engine(clean_url, pool_pre_ping=True, connect_args=connect_args)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


def build_session_factory(db_url: str | None = None) -> async_sessionmaker[AsyncSession]:
    """Fresh factory over a fresh engine (used by loop-sensitive callers that
    must create the engine inside their own event loop)."""
    target_url = db_url or settings.DATABASE_URL
    clean_url, connect_args = _get_asyncpg_clean_url_and_args(target_url)
    engine = create_async_engine(clean_url, pool_pre_ping=True, connect_args=connect_args)
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a session, always closed after the request."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
