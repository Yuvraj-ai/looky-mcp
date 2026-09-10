"""Shared test fixtures: ephemeral Postgres (pgserver), migrated schema, engine, session.

Each pytest session gets a dedicated database inside a pgserver-managed Postgres
instance. Alembic migrations run to head at session start, so tests always
exercise real migration output (Architecture §5 schema) against real Postgres.
"""

import os
import pathlib

import pgserver
import pytest
import pytest_asyncio

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-not-a-real-one-aaaaaaaaaaaaaaaaaaaaaaaa")
os.environ.setdefault("VISION_ENCRYPTION_KEY", "WJj1lZ0vLZe8VQZtqC7RxOOBUxNDNCENJmG-Dz2ElBc=")

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
PG_DIR = BACKEND_DIR / ".pgdata-test"


@pytest.fixture(scope="session")
def pg():
    server = pgserver.get_server(PG_DIR)
    yield server


@pytest.fixture(scope="session")
def pg_host(pg) -> str:
    return str(pg.get_uri().split("host=")[1])


@pytest.fixture(scope="session")
def db_engine_url(pg, pg_host) -> str:
    """Fresh per-session DB; asyncpg (SQLAlchemy async) URL."""
    import asyncio

    import asyncpg

    async def create() -> None:
        conn = await asyncpg.connect(host=pg_host, user="postgres", database="postgres")
        await conn.execute('DROP DATABASE IF EXISTS "vision_test" WITH (FORCE)')
        await conn.execute('CREATE DATABASE "vision_test"')
        await conn.close()

    asyncio.run(create())
    return f"postgresql+asyncpg://postgres:@/vision_test?host={pg_host}"


@pytest.fixture(scope="session")
def migrated_db(db_engine_url, pg_host) -> str:
    """Run Alembic migrations to head against the session DB (pg8000 sync URL)."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option(
        "sqlalchemy.url",
        f"postgresql+pg8000://postgres:@/vision_test" f"?unix_sock={pg_host}/.s.PGSQL.5432",
    )
    command.upgrade(cfg, "head")
    return db_engine_url


@pytest_asyncio.fixture
async def db_engine(migrated_db: str):
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(migrated_db)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
