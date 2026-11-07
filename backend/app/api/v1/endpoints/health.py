"""Health, liveness, and readiness diagnostic endpoints."""

from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.core.dependencies import get_redis_client
from app.core.logging import logger
from app.db.session import engine
from app.schemas.health import (
    ApiHealthResponse,
    HealthLiveResponse,
    HealthReadyResponse,
)

router = APIRouter()


async def check_database_connectivity() -> bool:
    """Execute simple ping query against PostgreSQL."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as exc:
        logger.warning(f"Database readiness check failed: {exc}")
        return False


async def check_redis_connectivity(request: Request) -> bool:
    """Execute ping command against Redis."""
    app = getattr(request, "app", None)
    client = getattr(app.state, "redis", None) if app and hasattr(app, "state") else None
    if client is not None:
        try:
            return bool(await client.ping())
        except Exception as exc:
            logger.warning(f"Redis state ping failed: {exc}")
            return False

    # Fallback to independent connection
    try:
        temp_client = get_redis_client()
        try:
            return bool(await temp_client.ping())
        finally:
            await temp_client.aclose()
    except Exception as exc:
        logger.warning(f"Redis independent ping failed: {exc}")
        return False


@router.get(
    "/live",
    response_model=HealthLiveResponse,
    summary="Liveness Probe",
    description="Returns 200 ALIVE as long as the application process is running. Never fails on external dependency downtime.",
)
async def liveness_probe() -> HealthLiveResponse:
    """Liveness probe for orchestrators (Kubernetes / ECS)."""
    return HealthLiveResponse(
        status="ALIVE",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/ready",
    response_model=HealthReadyResponse,
    responses={
        200: {"description": "All critical dependencies are healthy"},
        503: {"description": "One or more critical dependencies are down"},
    },
    summary="Readiness Probe",
    description="Checks live connectivity to PostgreSQL and Redis. Returns 200 READY or 503 UNAVAILABLE.",
)
async def readiness_probe(request: Request) -> JSONResponse:
    """Readiness probe checking PostgreSQL and Redis connectivity."""
    db_ok = await check_database_connectivity()
    redis_ok = await check_redis_connectivity(request)

    all_ready = db_ok and redis_ok
    status_text = "READY" if all_ready else "UNAVAILABLE"
    status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    payload = {
        "status": status_text,
        "checks": {
            "database": "UP" if db_ok else "DOWN",
            "redis": "UP" if redis_ok else "DOWN",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return JSONResponse(status_code=status_code, content=payload)


@router.get(
    "",
    response_model=ApiHealthResponse,
    include_in_schema=False,
)
@router.get(
    "/",
    response_model=ApiHealthResponse,
    summary="API Health Status",
    description="Returns API service version, environment, and subsystem health status.",
)
async def api_health(request: Request) -> ApiHealthResponse:
    """Detailed versioned health status endpoint."""
    settings = get_settings()
    db_ok = await check_database_connectivity()
    redis_ok = await check_redis_connectivity(request)

    subsystems: dict[str, str] = {
        "database": "UP" if db_ok else "DOWN",
        "redis": "UP" if redis_ok else "DOWN",
    }
    overall_status = "HEALTHY" if (db_ok and redis_ok) else "DEGRADED"

    return ApiHealthResponse(
        status=overall_status,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        subsystems=subsystems,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
