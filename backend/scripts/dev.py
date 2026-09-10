"""Dev entry: run uvicorn with a live pgserver Postgres (no system Postgres needed).

Usage: uv run python scripts/dev.py  (or: uv run python scripts/dev.py --migrate)
"""

import os
import pathlib
import sys

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent


def ensure_env() -> None:
    os.chdir(BACKEND_DIR)
    sys.path.insert(0, str(BACKEND_DIR))


def start_postgres() -> None:
    import pgserver

    data_dir = BACKEND_DIR / ".pgdata"
    server = pgserver.get_server(data_dir)
    uri = server.get_uri()
    host = uri.split("host=")[1]

    # ensure app database exists (first run)
    import asyncio

    import asyncpg

    async def ensure_db() -> None:
        conn = await asyncpg.connect(host=host, user="postgres", database="postgres")
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'vision_mcp'")
        if not exists:
            await conn.execute('CREATE DATABASE "vision_mcp"')
        await conn.close()

    asyncio.run(ensure_db())

    # .env already points at this instance via socket dir
    env_file = BACKEND_DIR / ".env"
    wanted = f"DATABASE_URL=postgresql+asyncpg://postgres:@/vision_mcp?host={host}"
    lines = []
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                continue
            lines.append(line)
    lines.insert(0, wanted)
    env_file.write_text("\n".join(lines) + "\n")


def main() -> None:
    ensure_env()
    start_postgres()
    if "--migrate" in sys.argv:
        # run migrations in a subprocess so the pg8000 sync URL doesn't leak
        # into this process's env (the app itself needs the asyncpg URL)
        import subprocess

        sock = f"{BACKEND_DIR}/.pgdata/.s.PGSQL.5432"
        env = dict(os.environ)
        env["DATABASE_URL"] = f"postgresql+pg8000://postgres:@/vision_mcp?unix_sock={sock}"
        subprocess.run(["uv", "run", "alembic", "upgrade", "head"], env=env, check=True)
        print("migrations applied")

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )
    # keep pgserver alive until uvicorn exits — pgserver stops on interpreter exit


if __name__ == "__main__":
    main()
