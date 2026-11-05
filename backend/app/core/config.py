"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Authoritative application settings with safe development defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Project metadata
    PROJECT_NAME: str = "Gadispot API"
    VERSION: str = "2.3.0"
    API_V1_STR: str = "/api/v1"

    # Environment & runtime
    ENVIRONMENT: str = Field(
        default="development", description="Runtime environment: development, test, staging, production"
    )
    DEBUG: bool = Field(default=False, description="Enable debug mode and detailed diagnostics")
    LOG_LEVEL: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # PostgreSQL Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/gadispot_test",
        description="Async PostgreSQL connection string",
    )
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 10

    # Redis Cache & Lock
    REDIS_URL: str = Field(
        default="redis://127.0.0.1:6379/0",
        description="Redis connection URL",
    )
    REDIS_PROTOCOL: int = Field(
        default=2,
        description="Redis RESP protocol version (2 or 3). Default 2 for maximum compatibility",
    )
    REDIS_SOCKET_TIMEOUT: float = 5.0
    REDIS_SOCKET_CONNECT_TIMEOUT: float = 5.0

    # Security & Tokens
    SECRET_KEY: str = Field(
        default="development-insecure-secret-key-change-in-production-min32chars",
        description="Cryptographic secret key for signing internal tokens",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS Configuration
    CORS_ORIGINS: list[str] | str = Field(
        default=["*"],
        description="Allowed CORS origins list or comma-separated string",
    )

    # External Provider Placeholders (Optional in development)
    FIREBASE_PROJECT_ID: str = ""
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    CASHFREE_APP_ID: str = ""
    CASHFREE_SECRET_KEY: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        """Ensure postgresql+asyncpg driver prefix is applied."""
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated string or preserve list of allowed CORS origins."""
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            return [i.strip() for i in v.split(",") if i.strip()]
        if isinstance(v, list):
            return [str(i).strip() for i in v if str(i).strip()]
        return ["*"]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.ENVIRONMENT.lower() == "test"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
