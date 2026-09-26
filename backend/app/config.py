"""Application configuration loaded from environment variables (Architecture §22)."""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    APP_SECRET_KEY: str
    VISION_ENCRYPTION_KEY: str
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    CORS_ALLOWED_ORIGIN: str = "http://localhost:5173"
    VISION_PROVIDER_TIMEOUT_SECONDS: int = 60

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = "postgresql+asyncpg://" + v[len("postgres://"):]
            elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
                v = "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
