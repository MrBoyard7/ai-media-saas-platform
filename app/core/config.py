"""
Centralized application configuration.

All runtime configuration is loaded from environment variables (or a `.env`
file in local development) so that the exact same container image can be
promoted from staging to production without being rebuilt.
"""
from functools import lru_cache
from typing import List

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Every setting has a safe local-development default so the project can be
    booted with `docker-compose up` without any manual configuration step.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General -----------------------------------------------------------
    APP_NAME: str = "AI Media SaaS Platform"
    APP_ENV: str = Field(default="local", description="local | staging | production")
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # --- Security ------------------------------------------------------------
    SECRET_KEY: str = Field(default="CHANGE-ME-IN-PRODUCTION")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- Supabase (self-hosted) ---------------------------------------------
    SUPABASE_URL: str = Field(default="http://localhost:8000")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="")
    SUPABASE_JWT_SECRET: str = Field(default="CHANGE-ME-IN-PRODUCTION")

    # --- Database ------------------------------------------------------------
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_media_platform"
    )

    # --- Redis / Celery --------------------------------------------------------
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")

    # --- CORS ------------------------------------------------------------------
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- GPU / Provider infrastructure ------------------------------------------
    RUNPOD_API_KEY: str = Field(default="")
    RUNPOD_ENDPOINT_ID: str = Field(default="")
    STORAGE_BUCKET_URL: AnyUrl | None = None

    # --- Credits -----------------------------------------------------------------
    DEFAULT_SIGNUP_CREDITS: int = 100
    LOW_BALANCE_WARNING_THRESHOLD: int = 20


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton for the process lifetime)."""
    return Settings()
