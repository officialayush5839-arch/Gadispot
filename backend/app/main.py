"""FastAPI application factory, lifespan context, middlewares, and exception handlers."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    DomainException,
    create_problem_details_response,
)
from app.core.logging import logger, setup_logging
from app.core.security import generate_request_id
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager handling application startup and shutdown lifecycle."""
    settings: Settings = getattr(app.state, "settings", None) or get_settings()
    setup_logging(log_level=settings.LOG_LEVEL, use_json=settings.is_production)

    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")

    # Initialize and verify Redis connection
    redis_client = None
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            protocol=settings.REDIS_PROTOCOL,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
        )
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info(f"Connected to Redis at {settings.REDIS_URL}")
    except Exception as exc:
        logger.warning(f"Could not connect to Redis at startup: {exc}")
        app.state.redis = redis_client

    # Verify PostgreSQL connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Connected to PostgreSQL database successfully")
    except Exception as exc:
        logger.warning(f"Could not connect to PostgreSQL database at startup: {exc}")

    yield

    # Shutdown sequence
    logger.info(f"Shutting down {settings.PROJECT_NAME}")
    if getattr(app.state, "redis", None) is not None:
        try:
            await app.state.redis.aclose()
            logger.info("Closed Redis connection pool")
        except Exception as exc:
            logger.warning(f"Error closing Redis client: {exc}")


def create_app(settings: Settings | None = None) -> FastAPI:
    """FastAPI application factory."""
    app_settings = settings or get_settings()

    app = FastAPI(
        title=app_settings.PROJECT_NAME,
        version=app_settings.VERSION,
        openapi_url=f"{app_settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.state.settings = app_settings

    # 1. CORS Middleware
    origins = app_settings.CORS_ORIGINS if isinstance(app_settings.CORS_ORIGINS, list) else [app_settings.CORS_ORIGINS]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Request Correlation ID Middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        incoming_id = request.headers.get("X-Request-ID")
        req_id = incoming_id.strip() if incoming_id and incoming_id.strip() else generate_request_id()
        request.state.request_id = req_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    # 3. Global Exception Handlers (RFC 7807 Problem Details)
    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
        req_id = getattr(request.state, "request_id", None)
        headers = {"X-Request-ID": req_id} if req_id else None
        return create_problem_details_response(
            status=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            code=exc.code,
            type_uri=exc.type_uri,
            instance=request.url.path,
            extra=exc.extra,
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        req_id = getattr(request.state, "request_id", None)
        headers = {"X-Request-ID": req_id} if req_id else None
        raw_errors = jsonable_encoder(exc.errors())
        status_code = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
        return create_problem_details_response(
            status=status_code,
            title="Validation Error",
            detail="Request validation failed for one or more fields.",
            code="VALIDATION_ERROR",
            instance=request.url.path,
            extra={"errors": raw_errors},
            headers=headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        req_id = getattr(request.state, "request_id", None)
        headers = {"X-Request-ID": req_id} if req_id else {}
        if exc.headers:
            headers.update(exc.headers)

        titles = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            409: "Conflict",
            422: "Unprocessable Entity",
            500: "Internal Server Error",
            503: "Service Unavailable",
        }
        title = titles.get(exc.status_code, "HTTP Error")
        code = title.upper().replace(" ", "_")

        return create_problem_details_response(
            status=exc.status_code,
            title=title,
            detail=str(exc.detail),
            code=code,
            instance=request.url.path,
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        req_id = getattr(request.state, "request_id", None)
        logger.exception(f"Unhandled server exception [req_id={req_id}]: {exc}")
        headers = {"X-Request-ID": req_id} if req_id else None

        detail = str(exc) if app_settings.DEBUG else "An unexpected internal server error occurred."
        return create_problem_details_response(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Internal Server Error",
            detail=detail,
            code="INTERNAL_SERVER_ERROR",
            instance=request.url.path,
            headers=headers,
        )

    # 4. Route Registration
    # Root health endpoints (/health/live, /health/ready) for cluster probes
    app.include_router(health_router, prefix="/health", tags=["Root Health Probes"])
    # API v1 routes (/api/v1/health, etc.)
    app.include_router(api_router, prefix=app_settings.API_V1_STR)

    return app


# Default application instance for ASGI servers (uvicorn app.main:app)
app = create_app()
