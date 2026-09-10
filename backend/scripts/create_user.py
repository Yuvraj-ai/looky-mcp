"""Admin user provisioning — the ONLY way users are created (no public signup).

Usage:
  uv run python scripts/create_user.py --email a@b.c --password 'secret'
  uv run python scripts/create_user.py --email a@b.c --google-sub '1234567890'

Uses DATABASE_URL from .env by default; override with --database-url
(any SQLAlchemy URL; asyncpg URL from .env is converted for sync use).
"""

import argparse
import asyncio
import sys

sys.path.insert(0, ".")


def _to_async_url(url: str) -> str:
    """Accept any URL; convert pg8000 sync test URLs to asyncpg."""
    if "+pg8000" in url:
        if "unix_sock" in url:
            base, sock = url.split("?unix_sock=")
            base = base.replace("+pg8000", "+asyncpg")
            host = sock.rsplit("/.s.PGSQL.5432", 1)[0]
            return f"{base}?host={host}"
        return url.replace("+pg8000", "+asyncpg")
    return url


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision a Vision MCP user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", help="initial password (email/password login)")
    parser.add_argument("--google-sub", help="pre-linked Google account subject")
    parser.add_argument(
        "--database-url",
        default=None,
        help="SQLAlchemy URL (defaults to DATABASE_URL env / .env)",
    )
    args = parser.parse_args()

    if not args.password and not args.google_sub:
        parser.error("provide --password and/or --google-sub")

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.auth.passwords import hash_password
    from app.config import settings
    from app.db import models

    async def run() -> int:
        engine = create_async_engine(_to_async_url(args.database_url or settings.DATABASE_URL))
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            existing = (
                await session.execute(select(models.User).where(models.User.email == args.email))
            ).scalar_one_or_none()
            if existing is not None:
                print(f"User {args.email} already exists", file=sys.stderr)
                return 1

            user = models.User(
                email=args.email,
                password_hash=hash_password(args.password) if args.password else None,
                google_sub=args.google_sub,
            )
            session.add(user)
            await session.commit()
            print(f"User {args.email} created")
        await engine.dispose()
        return 0

    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
