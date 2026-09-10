"""FastAPI application factory. Mounts REST API and MCP server (Architecture §1, §21)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth_routes, mcp_credential, system_prompts, vision_profiles
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

    app.include_router(auth_routes.router)
    app.include_router(system_prompts.router)
    app.include_router(vision_profiles.router)
    app.include_router(mcp_credential.router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
