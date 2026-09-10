"""Application configuration loaded from environment variables (Architecture §22)."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    APP_SECRET_KEY: str
    VISION_ENCRYPTION_KEY: str
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    CORS_ALLOWED_ORIGIN: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
