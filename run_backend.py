"""Start the Vision MCP backend (pgserver Postgres + migrations + uvicorn).

Usage:
  uv run python run_backend.py             # start server
  uv run python run_backend.py --migrate   # apply migrations, then start
"""

import pathlib
import subprocess
import sys

BACKEND = pathlib.Path(__file__).resolve().parent / "backend"

if __name__ == "__main__":
    sys.exit(
        subprocess.call(
            ["uv", "run", "python", "scripts/dev.py", *sys.argv[1:]],
            cwd=BACKEND,
        )
    )
