"""FastAPI application factory. Mounts REST API and MCP server (Architecture §1, §21)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # MCP session manager lifespan is wired here when /mcp is mounted (Phase 7).
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Vision MCP", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.CORS_ALLOWED_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
