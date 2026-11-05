"""Pydantic schemas for health and system diagnostic responses."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class HealthLiveResponse(BaseModel):
    """Schema for liveness probe response."""

    status: str = Field(default="ALIVE", description="Liveness state")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp",
    )


class HealthReadyChecks(BaseModel):
    """Component readiness status."""

    database: str = Field(description="Database connectivity status (UP/DOWN)")
    redis: str = Field(description="Redis connectivity status (UP/DOWN)")


class HealthReadyResponse(BaseModel):
    """Schema for readiness probe response."""

    status: str = Field(description="Readiness state (READY/UNAVAILABLE)")
    checks: HealthReadyChecks = Field(description="Individual dependency check states")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp",
    )


class ApiHealthResponse(BaseModel):
    """Schema for API versioned health response."""

    status: str = Field(description="Overall service health (HEALTHY/DEGRADED)")
    version: str = Field(description="Application version")
    environment: str = Field(description="Runtime environment")
    subsystems: dict[str, str] = Field(description="Subsystem health statuses")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp",
    )


class ProblemDetails(BaseModel):
    """RFC 7807 Problem Details response schema."""

    type: str = Field(description="URI reference that identifies the problem type")
    title: str = Field(description="Short human-readable summary of the problem type")
    status: int = Field(description="HTTP status code")
    detail: str = Field(description="Human-readable explanation specific to this occurrence")
    code: str = Field(description="Gadispot business error code")
    instance: str | None = Field(default=None, description="URI reference that identifies the specific occurrence")
    timestamp: str = Field(description="ISO 8601 UTC timestamp")
