"""Application configuration management."""

import os
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Team Pulse API"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost:5432/teampulse"
    )
    DATABASE_POOL_SIZE: int = Field(default=5)
    DATABASE_MAX_OVERFLOW: int = Field(default=10)

    # Authentication
    SECRET_KEY: str = Field(default="changeme-secret-key-for-development")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    # Redis (optional)
    REDIS_URL: Optional[str] = Field(default=None)
    CACHE_TTL: int = Field(default=300)  # 5 minutes

    # Rate Limiting
    RATE_LIMIT_DEFAULT: int = Field(default=100)  # requests per minute
    RATE_LIMIT_AUTHENTICATED: int = Field(default=1000)
    RATE_LIMIT_PULSE_SUBMISSION: int = Field(default=10)  # per hour

    # Email Configuration
    SMTP_HOST: Optional[str] = Field(default=None)
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    EMAIL_FROM: str = Field(default="noreply@teampulse.example.com")

    # Sentry
    SENTRY_DSN: Optional[str] = Field(default=None)

    # Pulse Configuration
    PULSE_REMINDER_ENABLED: bool = Field(default=True)
    PULSE_REMINDER_HOUR: int = Field(default=14)  # 2 PM
    PULSE_REMINDER_DAYS: List[int] = Field(default=[0, 2, 4])  # Mon, Wed, Fri

    # Trend Detection
    TREND_DETECTION_ENABLED: bool = Field(default=True)
    TREND_THRESHOLD: float = Field(default=0.5)  # Sentiment change threshold
    TREND_WINDOW_DAYS: int = Field(default=14)

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
