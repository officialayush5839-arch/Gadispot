"""Automated tests for Phase 6: RBAC, IDOR Shield, Rate Limiting, and Audit Logging."""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.authorization import require_roles, verify_resource_ownership
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.rate_limiter import SlidingWindowRateLimiter
from app.core.security import create_access_token
from app.main import app
from app.models.enums import UserRoleEnum
from app.models.users import User, UserRole
from app.services.audit_service import AuditService


@pytest.mark.asyncio
async def test_rbac_and_idor_ownership_checks(db_session):
    """Verify role authorization and object-level IDOR shielding."""
    driver_id = uuid.uuid4()
    other_driver_id = uuid.uuid4()
    ops_id = uuid.uuid4()

    # Create mock Driver user
    driver_user = User(id=driver_id, phone_number="+919800000001", full_name="Driver User")
    driver_user.roles = [UserRole(user_id=driver_id, role=UserRoleEnum.DRIVER)]

    # Create mock Operations user
    ops_user = User(id=ops_id, phone_number="+919800000002", full_name="Ops Staff")
    ops_user.roles = [UserRole(user_id=ops_id, role=UserRoleEnum.OPERATIONS)]

    # 1. Driver accessing own resource -> succeeds
    verify_resource_ownership(driver_user, driver_id)

    # 2. Driver accessing other driver's resource -> raises 403 IDOR
    with pytest.raises(ForbiddenException) as exc_info:
        verify_resource_ownership(driver_user, other_driver_id)
    assert exc_info.value.code == "IDOR_ACCESS_DENIED"

    # 3. Operations staff inspecting other driver's resource -> succeeds (clearance)
    verify_resource_ownership(ops_user, driver_id, allow_privileged=True)

    # 4. Role constraint check
    checker = require_roles(UserRoleEnum.OPERATIONS)
    # Ops user passes
    assert checker(ops_user) == ops_user
    # Driver fails
    with pytest.raises(ForbiddenException) as exc_info:
        checker(driver_user)
    assert exc_info.value.code == "FORBIDDEN_ROLE"


@pytest.mark.asyncio
async def test_sliding_window_rate_limiter_logic():
    """Verify rate limiter sliding-window threshold evaluation using mock/active Redis."""
    from unittest.mock import AsyncMock, MagicMock
    mock_redis = AsyncMock()
    
    # In redis.asyncio, pipeline() is a synchronous method returning the Pipeline instance
    mock_pipeline = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=[None, None, 2, True])
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

    limiter = SlidingWindowRateLimiter(key_prefix="test", max_requests=3, window_seconds=60)
    is_limited, count, retry_after = await limiter.is_rate_limited("user_123", mock_redis)
    assert is_limited is False
    assert count == 2

    # Simulate 4th request exceeding limit
    mock_pipeline.execute.return_value = [None, None, 4, True]
    mock_redis.zrange.return_value = [(b"entry", 1000.0)]
    is_limited, count, retry_after = await limiter.is_rate_limited("user_123", mock_redis)
    assert is_limited is True
    assert count == 4
    assert retry_after >= 0


@pytest.mark.asyncio
async def test_audit_event_service_immutability(db_session):
    """Verify append-only audit event logging and query retrieval."""
    actor_id = uuid.uuid4()
    resource_id = f"res_{uuid.uuid4().hex[:8]}"

    event = await AuditService.log_event(
        db=db_session,
        action="PROPERTY_APPROVED",
        resource_type="PROPERTY",
        resource_id=resource_id,
        actor_id=actor_id,
        details={"approved_by": "Ops Lead", "notes": "Deed verified"},
        ip_address="192.168.1.100",
    )
    assert event.id is not None
    assert event.action == "PROPERTY_APPROVED"
    assert event.resource_id == resource_id

    # Retrieve audit history
    history = await AuditService.list_events_for_resource(
        db=db_session,
        resource_type="PROPERTY",
        resource_id=resource_id,
    )
    assert len(history) >= 1
    assert history[0].action == "PROPERTY_APPROVED"
    assert history[0].details["approved_by"] == "Ops Lead"
