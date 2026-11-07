"""Tests for application settings and configuration management."""

import pytest
from app.core.config import Settings, get_settings


def test_settings_defaults():
    """Verify safe development default settings."""
    settings = Settings()
    assert settings.PROJECT_NAME == "Gadispot API"
    assert settings.VERSION == "2.3.0"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.ENVIRONMENT == "development"
    assert settings.DEBUG is False
    assert settings.LOG_LEVEL == "INFO"
    assert settings.REDIS_PROTOCOL == 2
    assert "postgresql+asyncpg://" in settings.DATABASE_URL
    assert settings.CORS_ORIGINS == ["*"]


def test_settings_database_url_normalization():
    """Verify automatic conversion of postgresql:// to postgresql+asyncpg://."""
    s1 = Settings(DATABASE_URL="postgresql://user:pass@localhost:5432/db")
    assert s1.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"

    s2 = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db")
    assert s2.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"


def test_settings_cors_origins_parsing():
    """Verify CORS origins string splitting and list parsing."""
    # Comma-separated string
    s1 = Settings(CORS_ORIGINS="http://localhost:3000, https://gadispot.in")
    assert s1.CORS_ORIGINS == ["http://localhost:3000", "https://gadispot.in"]

    # Single wildcard string
    s2 = Settings(CORS_ORIGINS="*")
    assert s2.CORS_ORIGINS == ["*"]

    # Explicit list
    s3 = Settings(CORS_ORIGINS=["http://app.gadispot.in", "http://localhost:8080"])
    assert s3.CORS_ORIGINS == ["http://app.gadispot.in", "http://localhost:8080"]


def test_settings_environment_flags():
    """Verify environment detection properties."""
    dev = Settings(ENVIRONMENT="development")
    assert dev.is_production is False
    assert dev.is_testing is False

    prod = Settings(
        ENVIRONMENT="production", PAYMENT_MODE="razorpay", DEMO_PAYMENTS_ENABLED=False
    )
    assert prod.is_production is True
    assert prod.is_testing is False

    test_env = Settings(ENVIRONMENT="test")
    assert test_env.is_production is False
    assert test_env.is_testing is True


def test_production_demo_mode_safety_guard():
    """Verify that enabling demo payment in production raises a strict ValidationError."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production", PAYMENT_MODE="demo", DEMO_PAYMENTS_ENABLED=True
        )


def test_get_settings_cached_singleton():
    """Verify get_settings returns identical cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
