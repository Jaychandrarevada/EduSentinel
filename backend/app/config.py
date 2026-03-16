"""
Centralised application configuration via Pydantic Settings.
All values are injected from environment variables / .env file.
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    APP_NAME: str = "EduSentinel API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://edu_user:password@localhost:5432/edusentinel"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ML Service
    ML_SERVICE_URL: str = "http://ml_service:8001"
    ML_REQUEST_TIMEOUT: int = 120

    # CORS — set to your Vercel domain in production, e.g.:
    #   CORS_ORIGINS=["https://edusentinel.vercel.app","http://localhost:3001"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Email / Notifications (optional — disabled by default)
    NOTIFICATION_ENABLED: bool = False
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "noreply@edusentinel.dev"

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        # Accept all PostgreSQL URL variants (postgres://, postgresql://, +asyncpg, +psycopg2)
        # and SQLite. Render.com provides the "postgres://" short form.
        if not v.startswith(("postgresql", "postgres", "sqlite")):
            raise ValueError("Only PostgreSQL and SQLite DATABASE_URLs are supported")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
