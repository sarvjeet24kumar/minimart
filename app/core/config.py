"""
MiniMart Application Configuration

Centralized configuration management using pydantic-settings.
All settings are loaded from environment variables.
"""

import json
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "MiniMart"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str
    TIMEZONE: str = "Asia/Kolkata"

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str
    REDIS_TOKEN_DB: int = 1

    # JWT Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int

    # Invitation Token
    INVITATION_TOKEN_EXPIRE_HOURS: int
    INVITATION_BASE_URL: str

    # Email Configuration
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str
    EMAIL_FROM_NAME: str = "MiniMart"

    # OTP Configuration
    OTP_EXPIRE_MINUTES: int
    OTP_LENGTH: int

    # Rate Limiting (Keeping these as defaults is standard as they are usually static)
    # Rate Limiting Thresholds
    RATE_LIMIT_AUTH: str = "5/minute"
    RATE_LIMIT_API: str = "30/minute"
    RATE_LIMIT_DEFAULT: str = "1000/minute"
    
    # Data Retention
    USER_UNVERIFIED_RETENTION_HOURS: int
    USER_DATA_RETENTION_DAYS: int
    TENANT_RETENTION_DAYS: int


    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [i.strip() for i in v.split(",")]
        return v

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
