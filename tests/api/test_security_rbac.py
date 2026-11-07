"""Automated tests for Phase 6: RBAC, IDOR Shield, Rate Limiting, and Audit Logging."""

import uuid

import pytest
from app.core.authorization import require_roles, verify_resource_ownership
from app.core.exceptions import ForbiddenException
from app.core.rate_limiter import SlidingWindowRateLimiter
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
    driver_user = User(
        id=driver_id, phone_number="+919800000001", full_name="Driver User"
    )
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

    limiter = SlidingWindowRateLimiter(
        key_prefix="test", max_requests=3, window_seconds=60
    )
    is_limited, count, retry_after = await limiter.is_rate_limited(
        "user_123", mock_redis
    )
    assert is_limited is False
    assert count == 2

    # Simulate 4th request exceeding limit
    mock_pipeline.execute.return_value = [None, None, 4, True]
    mock_redis.zrange.return_value = [(b"entry", 1000.0)]
    is_limited, count, retry_after = await limiter.is_rate_limited(
        "user_123", mock_redis
    )
    assert is_limited is True
    assert count == 4
    assert retry_after >= 0

    # Simulate Redis connection drop / failure: gracefully fail open
    import redis.asyncio as aioredis

    mock_pipeline.execute.side_effect = aioredis.ConnectionError(
        "Redis connection dropped"
    )
    is_limited, count, retry_after = await limiter.is_rate_limited(
        "user_123", mock_redis
    )
    assert is_limited is False
    assert count == 0
    assert retry_after == 0


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


@pytest.mark.asyncio
async def test_admin_cannot_access_unauthorized_routes_without_explicit_role():
    """Verify that ADMIN does not unilaterally bypass explicit role requirements."""
    admin_id = uuid.uuid4()
    admin_user = User(id=admin_id, phone_number="+919800000099", full_name="Admin User")
    admin_user.roles = [UserRole(user_id=admin_id, role=UserRoleEnum.ADMIN)]

    # Endpoint explicitly allows ONLY DRIVER
    driver_only_checker = require_roles(UserRoleEnum.DRIVER)
    with pytest.raises(ForbiddenException) as exc_info:
        driver_only_checker(admin_user)
    assert exc_info.value.code == "FORBIDDEN_ROLE"

    # Endpoint explicitly allows ADMIN -> passes
    admin_checker = require_roles(UserRoleEnum.ADMIN)
    assert admin_checker(admin_user) == admin_user


@pytest.mark.asyncio
async def test_canonical_role_aliases_recognized():
    """Verify PRD canonical aliases (SPACE_OWNER, SECURITY_GUARD, OPS) map correctly."""
    owner_id = uuid.uuid4()
    owner_user = User(
        id=owner_id, phone_number="+919800000088", full_name="Property Owner"
    )
    owner_user.roles = [UserRole(user_id=owner_id, role=UserRoleEnum.OWNER)]

    # Endpoint checks PRD canonical alias SPACE_OWNER
    space_owner_checker = require_roles("SPACE_OWNER")
    assert space_owner_checker(owner_user) == owner_user

    # Guard alias check
    guard_id = uuid.uuid4()
    guard_user = User(
        id=guard_id, phone_number="+919800000077", full_name="Security Guard"
    )
    guard_user.roles = [UserRole(user_id=guard_id, role=UserRoleEnum.GUARD)]

    security_guard_checker = require_roles("SECURITY_GUARD")
    assert security_guard_checker(guard_user) == guard_user


@pytest.mark.asyncio
async def test_rate_limiter_bounded_memory_cache_eviction():
    """Verify that SlidingWindowRateLimiter bounds memory usage and evicts expired keys during Redis outage."""
    import redis.asyncio as aioredis

    limiter = SlidingWindowRateLimiter(
        key_prefix="fail_closed_test",
        max_requests=2,
        window_seconds=10,
        fail_closed=True,
    )
    mock_redis = aioredis.from_url("redis://127.0.0.1:9999", socket_timeout=0.1)

    # First request: within limit
    is_limited, count, _ = await limiter.is_rate_limited("client_ip", mock_redis)
    assert is_limited is False
    assert count == 1

    # Second request: within limit
    is_limited, count, _ = await limiter.is_rate_limited("client_ip", mock_redis)
    assert is_limited is False
    assert count == 2

    # Third request: exceeds limit
    is_limited, count, retry_after = await limiter.is_rate_limited(
        "client_ip", mock_redis
    )
    assert is_limited is True
    assert count == 3
    assert retry_after >= 0

    # Test bounded pruning
    limiter._memory_cache["expired_key"] = [1.0]  # Old timestamp
    limiter._prune_memory_cache(now=1000.0)
    assert "expired_key" not in limiter._memory_cache


@pytest.mark.asyncio
async def test_admin_role_has_no_wildcard_permission():
    """Verify that ADMIN role does not grant wildcard '*' and enforces discrete least-privilege permissions."""
    from app.services.auth_service import get_permissions_for_roles, ROLE_PERMISSIONS

    admin_perms = get_permissions_for_roles(["ADMIN"])
    assert "*" not in admin_perms
    assert "*" not in ROLE_PERMISSIONS["ADMIN"]
    assert len(admin_perms) > 0
    # Must contain discrete admin operations
    assert "admin:users:manage" in admin_perms
    assert "admin:audit:read" in admin_perms
    assert "admin:system:configure" in admin_perms


@pytest.mark.asyncio
async def test_rate_limiter_lru_cap_eviction():
    """Verify that SlidingWindowRateLimiter deterministic OrderedDict LRU cache caps memory footprint."""
    from unittest.mock import AsyncMock, MagicMock
    from collections import OrderedDict
    import redis.asyncio as aioredis

    limiter = SlidingWindowRateLimiter(
        key_prefix="lru_test",
        max_requests=10,
        window_seconds=60,
        fail_closed=True,
        max_memory_keys=10,
    )

    mock_redis = AsyncMock()
    mock_pipeline = MagicMock()
    mock_pipeline.execute = AsyncMock(
        side_effect=aioredis.ConnectionError("Redis down")
    )
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

    assert isinstance(limiter._memory_cache, OrderedDict)

    # Insert 15 items when capacity is 10
    for i in range(15):
        await limiter.is_rate_limited(f"user_{i}", mock_redis)

    # Size must not exceed max_memory_keys (10)
    assert len(limiter._memory_cache) <= 10
    # Earliest items (user_0 .. user_4) should have been popped
    assert "ratelimit:lru_test:user_0" not in limiter._memory_cache
    assert "ratelimit:lru_test:user_14" in limiter._memory_cache
