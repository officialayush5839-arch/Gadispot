"""Comprehensive automated test suite for Phase 02 IAM Hardening:
1. Session persistence and SHA-256 refresh token storage.
2. Single-use refresh token rotation.
3. Cryptographic family reuse detection and family invalidation.
4. Explicit logout and session revocation.
5. Principal profile retrieval (GET /api/v1/auth/me).
6. Multi-role dynamic viewport switching and self-escalation defense.
7. Fail-closed rate limiting on auth paths.
8. Object-level IDOR shielding across bookings and access.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.rate_limiter import SlidingWindowRateLimiter
from app.core.security import create_access_token
from app.main import app
from app.models.enums import SpaceTypeEnum, UserRoleEnum, VehicleCategoryEnum
from app.models.parking import ParkingSpace
from app.models.reservations import SpaceReservation
from app.models.session import UserSession
from app.models.users import AccountStatus, User, UserRole, Vehicle
from app.services.audit_service import AuditService
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text


@pytest.mark.asyncio
async def test_session_creation_and_sha256_storage(db_session):
    """Verify session exchange persists SHA-256 hash (never plaintext) in user_sessions table."""
    client_ip = f"10.0.1.{uuid.uuid4().int % 250 + 1}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-driver:{phone}"},
            headers={"User-Agent": "TestClient/1.0", "X-Forwarded-For": client_ip},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        refresh_token = data["refresh_token"]

        user_id = uuid.UUID(data["user"]["id"])

        # Compute expected SHA-256 hash
        expected_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

        # Query user_sessions table
        stmt = select(UserSession).where(UserSession.user_id == user_id)
        sessions = (await db_session.execute(stmt)).scalars().all()
        assert len(sessions) == 1
        session_rec = sessions[0]
        assert session_rec.refresh_token_hash == expected_hash
        assert session_rec.is_revoked is False
        assert session_rec.family_id is not None
        assert session_rec.device_info == "TestClient/1.0"


@pytest.mark.asyncio
async def test_refresh_token_single_use_rotation(db_session):
    """Verify single-use token rotation: consuming a refresh token issues a new pair and revokes the old token."""
    client_ip = f"10.0.2.{uuid.uuid4().int % 250 + 1}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        login_resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-driver:{phone}"},
            headers={"X-Forwarded-For": client_ip},
        )
        assert login_resp.status_code == 200, login_resp.text
        first_refresh = login_resp.json()["refresh_token"]
        first_hash = hashlib.sha256(first_refresh.encode("utf-8")).hexdigest()

        # Execute refresh
        refresh_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": first_refresh},
            headers={"X-Forwarded-For": client_ip},
        )
        assert refresh_resp.status_code == 200, refresh_resp.text
        second_data = refresh_resp.json()
        second_refresh = second_data["refresh_token"]
        assert second_refresh != first_refresh
        second_hash = hashlib.sha256(second_refresh.encode("utf-8")).hexdigest()

        # Verify database session states
        stmt1 = select(UserSession).where(UserSession.refresh_token_hash == first_hash)
        old_session = (await db_session.execute(stmt1)).scalar_one()
        assert old_session.is_revoked is True
        assert old_session.revoked_at is not None

        stmt2 = select(UserSession).where(UserSession.refresh_token_hash == second_hash)
        new_session = (await db_session.execute(stmt2)).scalar_one()
        assert new_session.is_revoked is False
        # Cryptographic family ID must match across rotation
        assert new_session.family_id == old_session.family_id


@pytest.mark.asyncio
async def test_token_reuse_detection_and_family_invalidation(db_session):
    """Verify reuse detection: replaying a consumed refresh token immediately terminates the entire session family."""
    client_ip = f"10.0.3.{uuid.uuid4().int % 250 + 1}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        login_resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-driver:{phone}"},
            headers={"X-Forwarded-For": client_ip},
        )
        assert login_resp.status_code == 200, login_resp.text
        refresh_1 = login_resp.json()["refresh_token"]

        # Valid rotation 1: refresh_1 -> refresh_2
        rot_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_1},
            headers={"X-Forwarded-For": client_ip},
        )
        assert rot_resp.status_code == 200, rot_resp.text
        refresh_2 = rot_resp.json()["refresh_token"]

        # Artificially age the rotation past the grace period (15s ago) to test post-grace replay detection
        import hashlib
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import update
        from app.models.session import UserSession

        h1 = hashlib.sha256(refresh_1.encode()).hexdigest()
        await db_session.execute(
            update(UserSession)
            .where(UserSession.refresh_token_hash == h1)
            .values(revoked_at=datetime.now(timezone.utc) - timedelta(seconds=15))
        )
        await db_session.commit()

        # ATTACK: Replay refresh_1 (which has already been consumed and is outside grace period)
        replay_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_1},
            headers={"X-Forwarded-For": client_ip},
        )
        assert replay_resp.status_code == 401
        err_data = replay_resp.json()
        assert err_data["code"] == "TOKEN_REVOKED"
        assert "reuse detected" in err_data["detail"].lower()

        # Consequence: Legitimate refresh_2 must now ALSO be rejected because family was invalidated
        subsequent_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_2},
            headers={"X-Forwarded-For": client_ip},
        )
        assert subsequent_resp.status_code == 401
        assert subsequent_resp.json()["code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_logout_session_revocation(db_session):
    """Verify explicit logout revokes active sessions in database."""
    client_ip = f"10.0.4.{uuid.uuid4().int % 250 + 1}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        login_resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-driver:{phone}"},
            headers={"X-Forwarded-For": client_ip},
        )
        assert login_resp.status_code == 200, login_resp.text
        data = login_resp.json()
        access_tok = data["access_token"]
        refresh_tok = data["refresh_token"]

        # Call logout
        logout_resp = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_tok},
            headers={
                "Authorization": f"Bearer {access_tok}",
                "X-Forwarded-For": client_ip,
            },
        )
        assert logout_resp.status_code == 200
        assert logout_resp.json()["message"] == "Successfully logged out"

        # Verify session is marked revoked
        h = hashlib.sha256(refresh_tok.encode("utf-8")).hexdigest()
        stmt = select(UserSession).where(UserSession.refresh_token_hash == h)
        sess = (await db_session.execute(stmt)).scalar_one()
        assert sess.is_revoked is True


@pytest.mark.asyncio
async def test_get_current_user_profile_me(db_session):
    """Verify GET /api/v1/auth/me returns authenticated caller profile and role assignments."""
    client_ip = f"10.0.5.{uuid.uuid4().int % 250 + 1}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        login_resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-driver:{phone}"},
            headers={"X-Forwarded-For": client_ip},
        )
        assert login_resp.status_code == 200, login_resp.text
        access_tok = login_resp.json()["access_token"]

        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {access_tok}",
                "X-Forwarded-For": client_ip,
            },
        )
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["phone_number"] == phone
        assert "DRIVER" in me_data["roles"]
        assert me_data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_multi_role_switching_and_escalation_defense(db_session):
    """Verify role switching allows Driver <-> Owner swaps for assigned users and blocks unauthorized roles."""
    phone = f"+9198{uuid.uuid4().hex[:8]}"
    user = User(
        phone_number=phone,
        full_name="Dual Role User",
        status=AccountStatus.ACTIVE,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    # Assign both DRIVER and OWNER roles
    r1 = UserRole(user_id=user.id, role=UserRoleEnum.DRIVER)
    r2 = UserRole(user_id=user.id, role=UserRoleEnum.OWNER)
    db_session.add_all([r1, r2])
    await db_session.commit()

    token = create_access_token(
        subject=str(user.id),
        claims={"phone_number": phone, "roles": ["DRIVER", "SPACE_OWNER"]},
    )
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Switch to SPACE_OWNER -> succeeds
        switch_resp = await client.post(
            "/api/v1/auth/switch-role",
            json={"target_role": "SPACE_OWNER"},
            headers=headers,
        )
        assert switch_resp.status_code == 200
        assert switch_resp.json()["active_role"] == "SPACE_OWNER"

        # 2. Switch back to DRIVER -> succeeds
        switch_back = await client.post(
            "/api/v1/auth/switch-role",
            json={"target_role": "DRIVER"},
            headers=headers,
        )
        assert switch_back.status_code == 200
        assert switch_back.json()["active_role"] == "DRIVER"

        # 3. Escalation attack: attempt to switch to OPERATIONS or GUARD -> rejected with 403
        ops_attack = await client.post(
            "/api/v1/auth/switch-role",
            json={"target_role": "OPERATIONS"},
            headers=headers,
        )
        assert ops_attack.status_code == 403
        assert ops_attack.json()["code"] == "ROLE_SWITCH_PROHIBITED"

        guard_attack = await client.post(
            "/api/v1/auth/switch-role",
            json={"target_role": "GUARD"},
            headers=headers,
        )
        assert guard_attack.status_code == 403
        assert guard_attack.json()["code"] == "ROLE_SWITCH_PROHIBITED"


@pytest.mark.asyncio
async def test_fail_closed_rate_limiter_in_memory():
    """Verify rate limiter fails closed using in-memory sliding window cache when Redis is unavailable."""
    from unittest.mock import AsyncMock, MagicMock
    import redis.asyncio as aioredis

    mock_redis = AsyncMock()
    mock_pipeline = MagicMock()
    # Simulate Redis connection drop
    mock_pipeline.execute = AsyncMock(
        side_effect=aioredis.ConnectionError("Redis down")
    )
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

    limiter = SlidingWindowRateLimiter(
        key_prefix="auth_fail_closed",
        max_requests=2,
        window_seconds=60,
        fail_closed=True,
    )

    # First request: within limit -> False
    is_limited_1, count_1, _ = await limiter.is_rate_limited("client_ip_1", mock_redis)
    assert is_limited_1 is False
    assert count_1 == 1

    # Second request: within limit -> False
    is_limited_2, count_2, _ = await limiter.is_rate_limited("client_ip_1", mock_redis)
    assert is_limited_2 is False
    assert count_2 == 2

    # Third request: exceeded limit (max_requests=2) -> True (BLOCKED)
    is_limited_3, count_3, retry_after = await limiter.is_rate_limited(
        "client_ip_1", mock_redis
    )
    assert is_limited_3 is True
    assert count_3 == 3
    assert retry_after > 0


@pytest.mark.asyncio
async def test_booking_idor_shielding(db_session):
    """Verify GET /api/v1/bookings/{id} enforces object-level IDOR shielding."""
    # Driver 1
    driver1 = User(phone_number=f"+9198{uuid.uuid4().hex[:8]}", full_name="Driver One")
    db_session.add(driver1)

    # Driver 2
    driver2 = User(phone_number=f"+9198{uuid.uuid4().hex[:8]}", full_name="Driver Two")
    db_session.add(driver2)

    # Ops Staff
    ops_user = User(phone_number=f"+9198{uuid.uuid4().hex[:8]}", full_name="Ops Lead")
    db_session.add(ops_user)
    await db_session.flush()

    ops_role = UserRole(user_id=ops_user.id, role=UserRoleEnum.OPERATIONS)
    db_session.add(ops_role)

    # Create vehicle for Driver 1
    vehicle = Vehicle(
        driver_id=driver1.id,
        registration_plate=f"KA03ID{uuid.uuid4().hex[:4].upper()}",
        vehicle_category=VehicleCategoryEnum.SEDAN,
    )
    db_session.add(vehicle)

    # Create property
    prop_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO properties (id, owner_id, title, property_type, address_line, city, postal_code, location, is_active)
            VALUES (:id, :owner_id, 'IDOR Test Hub', 'COMMERCIAL_BUILDING', 'Indiranagar 100ft Rd', 'Bengaluru', '560038', 'SRID=4326;POINT(77.6412 12.9719)', TRUE)
            """
        ),
        {"id": prop_id, "owner_id": driver1.id},
    )

    space = ParkingSpace(
        property_id=prop_id,
        space_label=f"IDOR-BAY-{uuid.uuid4().hex[:4]}",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        base_hourly_rate_paise=5000,
    )
    db_session.add(space)
    await db_session.flush()

    res_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO space_reservations (id, parking_space_id, driver_id, vehicle_id, time_window, reservation_type, status, booking_reference, hold_expires_at)
            VALUES (:id, :space_id, :driver_id, :vehicle_id, tstzrange(NOW(), NOW() + INTERVAL '2 hours', '[)'), 'TEMPORARY_HOLD', 'ACTIVE_HOLD', :ref, NOW() + INTERVAL '480 seconds')
            """
        ),
        {
            "id": res_id,
            "space_id": space.id,
            "driver_id": driver1.id,
            "vehicle_id": vehicle.id,
            "ref": f"BK-IDOR-{uuid.uuid4().hex[:4]}",
        },
    )
    await db_session.commit()

    tok_driver1 = create_access_token(
        subject=str(driver1.id), claims={"roles": ["DRIVER"]}
    )
    tok_driver2 = create_access_token(
        subject=str(driver2.id), claims={"roles": ["DRIVER"]}
    )
    tok_ops = create_access_token(
        subject=str(ops_user.id), claims={"roles": ["OPERATIONS"]}
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Driver 1 views own reservation -> 200 OK
        resp1 = await client.get(
            f"/api/v1/bookings/{res_id}",
            headers={"Authorization": f"Bearer {tok_driver1}"},
        )
        assert resp1.status_code == 200
        assert resp1.json()["reservation_id"] == str(res_id)

        # 2. Driver 2 attempts IDOR access to Driver 1's reservation -> 403 Forbidden
        resp2 = await client.get(
            f"/api/v1/bookings/{res_id}",
            headers={"Authorization": f"Bearer {tok_driver2}"},
        )
        assert resp2.status_code == 403
        assert resp2.json()["code"] == "IDOR_ACCESS_DENIED"

        # 3. Operations staff views Driver 1's reservation -> 200 OK (inspection clearance)
        resp3 = await client.get(
            f"/api/v1/bookings/{res_id}",
            headers={"Authorization": f"Bearer {tok_ops}"},
        )
        assert resp3.status_code == 200
        assert resp3.json()["reservation_id"] == str(res_id)
