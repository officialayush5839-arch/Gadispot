"""Tests for API health checks, readiness probes, middleware, and RFC 7807 errors."""

import uuid

import app.api.v1.endpoints.health as health_module
import httpx
import pytest
from app.core.exceptions import (
    ConflictException,
    EntityNotFoundException,
)
from app.main import create_app
from fastapi import APIRouter
from pydantic import BaseModel

# Sample router to verify exception handling on routes
# Named 'sample_router' instead of 'test_router' to prevent pytest collection warnings
sample_router = APIRouter()


class SamplePayload(BaseModel):
    name: str
    count: int


@sample_router.get("/test/not-found")
async def trigger_not_found():
    raise EntityNotFoundException(
        detail="Parking space bay-42 was not found.",
        code="BAY_NOT_FOUND",
    )


@sample_router.get("/test/conflict")
async def trigger_conflict():
    raise ConflictException(
        detail="Bay is already reserved for the requested slot.",
        code="SLOT_INTERVAL_CONFLICT",
    )


@sample_router.post("/test/validation-body")
async def trigger_validation(payload: SamplePayload):
    return {"message": "ok", "data": payload.model_dump()}


@sample_router.get("/test/unhandled")
async def trigger_unhandled():
    raise RuntimeError("Unexpected internal crash for testing 500 handler")


@pytest.fixture
def app_instance():
    """Create a test application instance with sample diagnostic routes attached."""
    app = create_app()
    app.include_router(sample_router)
    return app


@pytest.fixture
async def client(app_instance):
    """AsyncClient fixture with raise_app_exceptions=False to test 500 RFC 7807 responses."""
    transport = httpx.ASGITransport(app=app_instance, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as ac:
        yield ac


# -----------------------------------------------------------------------------
# 1. Liveness & Readiness Probe Tests
# -----------------------------------------------------------------------------


async def test_liveness_probe_returns_alive(client):
    """GET /health/live must always return 200 OK and status ALIVE."""
    response = await client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ALIVE"
    assert "timestamp" in data


async def test_readiness_probe_success(client):
    """GET /health/ready returns 200 READY when all critical services are healthy."""
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["checks"]["database"] == "UP"
    assert data["checks"]["redis"] == "UP"
    assert "timestamp" in data


async def test_readiness_probe_database_failure(client, monkeypatch):
    """GET /health/ready returns 503 UNAVAILABLE when database is down."""

    async def mock_db_fail():
        return False

    monkeypatch.setattr(health_module, "check_database_connectivity", mock_db_fail)

    response = await client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "UNAVAILABLE"
    assert data["checks"]["database"] == "DOWN"
    assert data["checks"]["redis"] == "UP"


async def test_readiness_probe_redis_failure(client, monkeypatch):
    """GET /health/ready returns 503 UNAVAILABLE when Redis is down."""

    async def mock_redis_fail(request):
        return False

    monkeypatch.setattr(health_module, "check_redis_connectivity", mock_redis_fail)

    response = await client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "UNAVAILABLE"
    assert data["checks"]["database"] == "UP"
    assert data["checks"]["redis"] == "DOWN"


async def test_api_v1_health_status(client):
    """GET /api/v1/health returns detailed versioned health information."""
    for path in ["/api/v1/health", "/api/v1/health/"]:
        response = await client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "HEALTHY"
        assert data["version"] == "2.3.0"
        assert data["environment"] == "development"
        assert data["subsystems"]["database"] == "UP"
        assert data["subsystems"]["redis"] == "UP"


async def test_api_v1_health_degraded_when_subsystem_fails(client, monkeypatch):
    """GET /api/v1/health returns DEGRADED status when a dependency fails."""

    async def mock_db_fail():
        return False

    monkeypatch.setattr(health_module, "check_database_connectivity", mock_db_fail)

    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert data["subsystems"]["database"] == "DOWN"


# -----------------------------------------------------------------------------
# 2. Middleware Tests (Request ID & CORS)
# -----------------------------------------------------------------------------


async def test_request_id_middleware_generates_uuid_when_omitted(client):
    """Responses must contain an X-Request-ID header even if client omitted one."""
    response = await client.get("/health/live")
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    # Validate it is a valid UUID
    parsed_uuid = uuid.UUID(req_id)
    assert parsed_uuid.version == 4


async def test_request_id_middleware_preserves_client_provided_id(client):
    """Responses must echo back the client-supplied X-Request-ID header."""
    custom_id = "trace-client-id-987654"
    response = await client.get("/health/live", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


async def test_cors_headers_present(client):
    """Verify CORS headers are returned on cross-origin requests."""
    response = await client.get(
        "/health/live",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") in [
        "*",
        "http://localhost:3000",
    ]


# -----------------------------------------------------------------------------
# 3. RFC 7807 Problem Details Exception Handler Tests
# -----------------------------------------------------------------------------


async def test_rfc7807_not_found_exception(client):
    """EntityNotFoundException must produce RFC 7807 Problem Details JSON."""
    response = await client.get("/test/not-found")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"

    data = response.json()
    assert data["status"] == 404
    assert data["title"] == "Resource Not Found"
    assert data["code"] == "BAY_NOT_FOUND"
    assert data["detail"] == "Parking space bay-42 was not found."
    assert data["instance"] == "/test/not-found"
    assert "type" in data
    assert "timestamp" in data
    assert "X-Request-ID" in response.headers


async def test_rfc7807_conflict_exception(client):
    """ConflictException must produce 409 Conflict RFC 7807 Problem Details."""
    response = await client.get("/test/conflict")
    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"

    data = response.json()
    assert data["status"] == 409
    assert data["title"] == "State Conflict"
    assert data["code"] == "SLOT_INTERVAL_CONFLICT"
    assert data["detail"] == "Bay is already reserved for the requested slot."
    assert data["instance"] == "/test/conflict"


async def test_rfc7807_validation_error(client):
    """FastAPI RequestValidationError must produce 422 RFC 7807 Problem Details."""
    # Send invalid type for count (string instead of int)
    response = await client.post(
        "/test/validation-body",
        json={"name": "Test", "count": "not-an-integer"},
    )
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"

    data = response.json()
    assert data["status"] == 422
    assert data["title"] == "Validation Error"
    assert data["code"] == "VALIDATION_ERROR"
    assert "errors" in data
    assert len(data["errors"]) > 0


async def test_rfc7807_starlette_http_404(client):
    """Non-existent paths must return 404 RFC 7807 Problem Details."""
    response = await client.get("/non-existent-endpoint-route")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"

    data = response.json()
    assert data["status"] == 404
    assert data["title"] == "Not Found"
    assert data["code"] == "NOT_FOUND"


async def test_rfc7807_unhandled_exception(client):
    """Unhandled server errors must return 500 RFC 7807 Problem Details."""
    response = await client.get("/test/unhandled")
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"

    data = response.json()
    assert data["status"] == 500
    assert data["title"] == "Internal Server Error"
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    assert "timestamp" in data
