"""Unit and integration API test suite for Operating Schedules and Blackout Overlap Engine."""

import secrets
import uuid
from datetime import datetime

import asyncpg
import pytest
from app.core.security import create_access_token
from app.main import app
from app.models.enums import (
    AccountStatus,
    SpaceTypeEnum,
    UserRoleEnum,
    VehicleCategoryEnum,
)
from app.models.parking import ParkingSpace
from app.models.properties import OperatingSchedule, Property
from app.models.schedules import BlackoutSchedule
from app.models.users import User, UserRole
from app.services.property_service import PropertyService
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


async def _create_owner(db_session, suffix="sch") -> tuple[User, dict[str, str]]:
    """Helper to provision an active OWNER user with Bearer token."""
    phone = f"+9198{uuid.uuid4().hex[:8]}"
    user = User(
        phone_number=phone,
        full_name=f"Owner {suffix}",
        status=AccountStatus.ACTIVE,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role=UserRoleEnum.OWNER))
    await db_session.commit()

    token = create_access_token(
        subject=str(user.id),
        claims={"roles": [UserRoleEnum.OWNER.value], "phone_number": phone},
    )
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


async def _create_driver(db_session) -> tuple[User, dict[str, str]]:
    """Helper to provision an active DRIVER user with Bearer token."""
    phone = f"+9197{uuid.uuid4().hex[:8]}"
    user = User(
        phone_number=phone,
        full_name="Driver User",
        status=AccountStatus.ACTIVE,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role=UserRoleEnum.DRIVER))
    await db_session.commit()

    token = create_access_token(
        subject=str(user.id),
        claims={"roles": [UserRoleEnum.DRIVER.value], "phone_number": phone},
    )
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


async def _create_property_and_space(
    db_session, owner_id: uuid.UUID
) -> tuple[Property, ParkingSpace]:
    """Helper to persist a property and a parking space."""
    prop = Property(
        owner_id=owner_id,
        title="Schedule Test Plaza",
        property_type="COMMERCIAL_BUILDING",
        address_line="MG Road, Bengaluru",
        city="Bengaluru",
        postal_code="560001",
        location=PropertyService.make_point_wkt(12.9716, 77.5946),
        is_active=False,
    )
    db_session.add(prop)
    await db_session.flush()

    space = ParkingSpace(
        property_id=prop.id,
        space_label="BAY-SCH-1",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        length_meters=4.80,
        width_meters=2.40,
        height_clearance_meters=2.10,
        has_ev_charging=False,
        base_hourly_rate_paise=5000,
    )
    db_session.add(space)
    await db_session.commit()
    await db_session.refresh(prop)
    await db_session.refresh(space)
    return prop, space


# =============================================================================
# Operating Schedules Tests
# =============================================================================


@pytest.mark.asyncio
async def test_add_operating_schedule_success(db_session):
    """Verify owner configures a weekly recurring operating hours window."""
    owner, headers = await _create_owner(db_session, "op_ok")
    prop, _ = await _create_property_and_space(db_session, owner.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "day_of_week": 1,
            "start_time": "08:00:00",
            "end_time": "18:00:00",
            "is_active": True,
        }
        resp = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["day_of_week"] == 1
        assert data["start_time"] == "08:00:00"
        assert data["end_time"] == "18:00:00"
        assert data["is_active"] is True


@pytest.mark.asyncio
async def test_reject_overlapping_operating_schedules_same_day(db_session):
    """Verify overlapping operating schedule windows on the same day are rejected with 409 Conflict."""
    owner, headers = await _create_owner(db_session, "op_overlap")
    prop, _ = await _create_property_and_space(db_session, owner.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Window 1: 08:00 to 14:00 on Tuesday (day_of_week=1)
        resp1 = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 1, "start_time": "08:00:00", "end_time": "14:00:00"},
            headers=headers,
        )
        assert resp1.status_code == 201

        # Window 2: Overlapping 12:00 to 18:00 on Tuesday (day_of_week=1) -> 409 Conflict
        resp2 = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 1, "start_time": "12:00:00", "end_time": "18:00:00"},
            headers=headers,
        )
        assert resp2.status_code == 409
        assert resp2.json()["code"] == "SCHEDULE_OVERLAP_CONFLICT"


@pytest.mark.asyncio
async def test_reject_invalid_operating_schedule_times(db_session):
    """Verify inverted times (start >= end) and invalid day_of_week are rejected with 422."""
    owner, headers = await _create_owner(db_session, "op_inv")
    prop, _ = await _create_property_and_space(db_session, owner.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Inverted times: 18:00 to 08:00
        resp1 = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 2, "start_time": "18:00:00", "end_time": "08:00:00"},
            headers=headers,
        )
        assert resp1.status_code == 422

        # Invalid day (> 6)
        resp2 = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 7, "start_time": "08:00:00", "end_time": "18:00:00"},
            headers=headers,
        )
        assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_list_and_delete_operating_schedules(db_session):
    """Verify listing and deleting operating schedule windows with owner authorization."""
    owner, headers = await _create_owner(db_session, "op_del")
    prop, _ = await _create_property_and_space(db_session, owner.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Add schedule
        res = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 3, "start_time": "09:00:00", "end_time": "17:00:00"},
            headers=headers,
        )
        sch_id = res.json()["id"]

        # List schedules
        list_resp = await client.get(
            f"/api/v1/properties/{prop.id}/operating-hours", headers=headers
        )
        assert list_resp.status_code == 200
        assert any(s["id"] == sch_id for s in list_resp.json())

        # Delete schedule
        del_resp = await client.delete(
            f"/api/v1/properties/{prop.id}/operating-hours/{sch_id}",
            headers=headers,
        )
        assert del_resp.status_code == 204

        # Verify gone
        stmt = select(OperatingSchedule).where(OperatingSchedule.id == uuid.UUID(sch_id))
        assert (await db_session.execute(stmt)).scalar_one_or_none() is None


# =============================================================================
# Blackout Schedules Tests
# =============================================================================


@pytest.mark.asyncio
async def test_add_space_and_property_wide_blackouts(db_session):
    """Verify owner creates bay-specific and property-wide blackout windows."""
    owner, headers = await _create_owner(db_session, "bo_ok")
    prop, space = await _create_property_and_space(db_session, owner.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Bay-specific blackout
        bo1 = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={
                "start_time": "2026-12-15T08:00:00Z",
                "end_time": "2026-12-16T18:00:00Z",
                "reason": "Personal guest visit",
            },
            headers=headers,
        )
        assert bo1.status_code == 201, bo1.text
        assert bo1.json()["parking_space_id"] == str(space.id)
        assert bo1.json()["is_active"] is True

        # 2. Property-wide blackout
        bo2 = await client.post(
            f"/api/v1/properties/{prop.id}/blackouts",
            json={
                "start_time": "2026-12-24T00:00:00Z",
                "end_time": "2026-12-25T23:59:59Z",
                "reason": "Holiday site maintenance",
            },
            headers=headers,
        )
        assert bo2.status_code == 201
        assert bo2.json()["parking_space_id"] is None


@pytest.mark.asyncio
async def test_reject_overlapping_active_blackouts(db_session):
    """Verify overlapping blackout windows on the same space or property return 409 Conflict."""
    owner, headers = await _create_owner(db_session, "bo_overlap")
    _prop, space = await _create_property_and_space(db_session, owner.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Blackout 1: Dec 18 18:00 to Dec 21 08:00
        res1 = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={
                "start_time": "2026-12-18T18:00:00Z",
                "end_time": "2026-12-21T08:00:00Z",
                "reason": "Family wedding",
            },
            headers=headers,
        )
        assert res1.status_code == 201

        # Blackout 2: Overlapping Dec 19 00:00 to Dec 20 00:00 -> 409 Conflict
        res2 = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={
                "start_time": "2026-12-19T00:00:00Z",
                "end_time": "2026-12-20T00:00:00Z",
                "reason": "Conflicting block",
            },
            headers=headers,
        )
        assert res2.status_code == 409
        assert res2.json()["code"] == "BLACKOUT_OVERLAP_CONFLICT"


@pytest.mark.asyncio
async def test_reject_blackout_overlapping_confirmed_reservation(db_session):
    """Verify blackout creation conflicting with confirmed driver reservation returns HTTP 409 Conflict."""
    owner, headers = await _create_owner(db_session, "bo_resv_conflict")
    _prop, space = await _create_property_and_space(db_session, owner.id)

    # Insert a vehicle and a confirmed driver reservation directly into space_reservations table
    veh_id = uuid.uuid4()
    resv_id = uuid.uuid4()
    st = datetime.fromisoformat("2026-12-05T10:00:00+00:00")
    et = datetime.fromisoformat("2026-12-05T14:00:00+00:00")
    time_window = asyncpg.Range(st, et, lower_inc=True, upper_inc=False)

    conn = await db_session.connection()
    raw_conn = await conn.get_raw_connection()
    await raw_conn.driver_connection.execute(
        """
        INSERT INTO vehicles (
            id, driver_id, registration_plate, vehicle_category
        ) VALUES (
            $1, $2, $3, 'SEDAN'
        )
        """,
        veh_id,
        owner.id,
        f"KA01AB{secrets.token_hex(2).upper()}",
    )
    await raw_conn.driver_connection.execute(
        """
        INSERT INTO space_reservations (
            id, parking_space_id, driver_id, vehicle_id,
            time_window, reservation_type, status, booking_reference
        ) VALUES (
            $1, $2, $3, $4,
            $5, 'CONFIRMED_BOOKING', 'CONFIRMED', $6
        )
        """,
        resv_id,
        space.id,
        owner.id,
        veh_id,
        time_window,
        f"BK-{secrets.token_hex(4).upper()}",
    )
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Attempt blackout overlapping the confirmed booking window (10:00 to 14:00)
        resp = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={
                "start_time": "2026-12-05T09:00:00Z",
                "end_time": "2026-12-05T15:00:00Z",
                "reason": "Overlapping blackout on confirmed booking",
            },
            headers=headers,
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "RESERVATION_OVERLAP_CONFLICT"


@pytest.mark.asyncio
async def test_delete_blackout_and_cancel_lifecycle(db_session):
    """Verify cancelling a blackout schedule removes it or renders it inactive."""
    owner, headers = await _create_owner(db_session, "bo_del")
    _prop, space = await _create_property_and_space(db_session, owner.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create blackout
        res = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={
                "start_time": "2026-12-28T08:00:00Z",
                "end_time": "2026-12-29T18:00:00Z",
                "reason": "Temporary bay repair",
            },
            headers=headers,
        )
        bo_id = res.json()["id"]

        # Cancel blackout
        del_resp = await client.delete(
            f"/api/v1/spaces/{space.id}/blackouts/{bo_id}", headers=headers
        )
        assert del_resp.status_code == 204

        # Check DB
        stmt = select(BlackoutSchedule).where(BlackoutSchedule.id == uuid.UUID(bo_id))
        bo_row = (await db_session.execute(stmt)).scalar_one_or_none()
        assert bo_row is None or bo_row.is_active is False


@pytest.mark.asyncio
async def test_schedules_unauthorized_driver_rejected(db_session):
    """Verify DRIVER role cannot configure operating hours or blackouts (HTTP 403 Forbidden)."""
    owner, _ = await _create_owner(db_session, "sec_owner")
    _driver, driver_headers = await _create_driver(db_session)
    prop, space = await _create_property_and_space(db_session, owner.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Operating hours -> 403
        r1 = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 0, "start_time": "08:00:00", "end_time": "18:00:00"},
            headers=driver_headers,
        )
        assert r1.status_code == 403

        # Blackouts -> 403
        r2 = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={
                "start_time": "2026-12-30T00:00:00Z",
                "end_time": "2026-12-30T23:59:59Z",
            },
            headers=driver_headers,
        )
        assert r2.status_code == 403
