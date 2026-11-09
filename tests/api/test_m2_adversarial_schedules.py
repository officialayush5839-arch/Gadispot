"""Adversarial stress and boundary test suite for Gadispot Phase 03 Milestone 2.

Covers:
1. 3D Physical Clearance Boundaries (exact tolerance, 1mm overflow on L/W/H).
2. EV Charging Compatibility Matrix (driver requested vs optional, non-EV vs EV bays).
3. Duplicate Space Labels (uniqueness within property, allowed across properties, mutation collisions).
4. Operating Hours Overlap (exact duplicate, subsets, supersets, touching/abutting boundaries).
5. Blackout Schedule Collision Matrix (blackout overlapping blackout, blackout overlapping reservations).
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

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


async def _create_owner(db_session, suffix: str = "adv") -> tuple[User, dict[str, str]]:
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
        claims={"roles": [UserRoleEnum.OWNER.value, "SPACE_OWNER"], "phone_number": phone},
    )
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


async def _create_property(
    db_session, owner_id: uuid.UUID, title: str = "Adversarial Property", lat: float = 12.9716, lon: float = 77.5946
) -> Property:
    """Helper to persist a property in the database."""
    prop = Property(
        owner_id=owner_id,
        title=title,
        property_type="COMMERCIAL_BUILDING",
        address_line="100 Feet Road, Indiranagar",
        city="Bengaluru",
        postal_code="560038",
        location=PropertyService.make_point_wkt(lat, lon),
        is_active=False,
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)
    return prop


# =============================================================================
# 1. 3D Physical Clearance Boundaries
# =============================================================================


@pytest.mark.asyncio
async def test_adversarial_3d_clearance_boundaries(db_session):
    """Verify exact 3D clearance boundaries and sub-millimeter / 1mm overflow rejections.

    Bay Dimensions: 5.0m L (5000mm) x 2.4m W (2400mm) x 2.0m H (2000mm).
    Required Margins: +0.3m (300mm) L, +0.4m (400mm) W, +0.1m (100mm) H.
    Maximum allowed vehicle: 4700mm L x 2000mm W x 1900mm H.
    """
    owner, headers = await _create_owner(db_session, "adv_3d")
    prop = await _create_property(db_session, owner.id, "Clearance Test Prop")

    # Create bay with exact dimensions: 5.00m L, 2.40m W, 2.00m H
    space = ParkingSpace(
        property_id=prop.id,
        space_label="BAY-3D-BOUND",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        length_meters=Decimal("5.00"),
        width_meters=Decimal("2.40"),
        height_clearance_meters=Decimal("2.00"),
        has_ev_charging=False,
        base_hourly_rate_paise=5000,
    )
    db_session.add(space)
    await db_session.commit()
    await db_session.refresh(space)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Case A: Exactly matching clearance boundary (4.7m L x 2.0m W x 1.9m H) -> MUST PASS
        resp_exact = await client.post(
            f"/api/v1/spaces/{space.id}/compatibility",
            json={
                "vehicle_category": "SEDAN",
                "vehicle_length_mm": 4700,
                "vehicle_width_mm": 2000,
                "vehicle_height_mm": 1900,
                "is_ev": False,
            },
            headers=headers,
        )
        assert resp_exact.status_code == 200, resp_exact.text
        data_exact = resp_exact.json()
        assert data_exact["is_compatible"] is True
        assert data_exact["method"] == "3d_clearance"
        assert data_exact["length_clearance_mm"] == 300
        assert data_exact["width_clearance_mm"] == 400
        assert data_exact["height_clearance_mm"] == 100
        assert data_exact["rejection_reasons"] == []

        # Case B: 1mm over length (4.701m = 4701mm) -> MUST FAIL
        resp_len_over = await client.post(
            f"/api/v1/spaces/{space.id}/compatibility",
            json={
                "vehicle_category": "SEDAN",
                "vehicle_length_mm": 4701,
                "vehicle_width_mm": 2000,
                "vehicle_height_mm": 1900,
                "is_ev": False,
            },
            headers=headers,
        )
        assert resp_len_over.status_code == 200
        data_len = resp_len_over.json()
        assert data_len["is_compatible"] is False
        assert data_len["length_clearance_mm"] == 299
        assert any("length clearance" in r.lower() for r in data_len["rejection_reasons"])
        assert not any("width" in r.lower() for r in data_len["rejection_reasons"])
        assert not any("height" in r.lower() for r in data_len["rejection_reasons"])

        # Case C: 1mm over width (2.001m = 2001mm) -> MUST FAIL
        resp_wid_over = await client.post(
            f"/api/v1/spaces/{space.id}/compatibility",
            json={
                "vehicle_category": "SEDAN",
                "vehicle_length_mm": 4700,
                "vehicle_width_mm": 2001,
                "vehicle_height_mm": 1900,
                "is_ev": False,
            },
            headers=headers,
        )
        assert resp_wid_over.status_code == 200
        data_wid = resp_wid_over.json()
        assert data_wid["is_compatible"] is False
        assert data_wid["width_clearance_mm"] == 399
        assert any("width clearance" in r.lower() for r in data_wid["rejection_reasons"])
        assert not any("length" in r.lower() for r in data_wid["rejection_reasons"])
        assert not any("height" in r.lower() for r in data_wid["rejection_reasons"])

        # Case D: 1mm over height (1.901m = 1901mm) -> MUST FAIL
        resp_hgt_over = await client.post(
            f"/api/v1/spaces/{space.id}/compatibility",
            json={
                "vehicle_category": "SEDAN",
                "vehicle_length_mm": 4700,
                "vehicle_width_mm": 2000,
                "vehicle_height_mm": 1901,
                "is_ev": False,
            },
            headers=headers,
        )
        assert resp_hgt_over.status_code == 200
        data_hgt = resp_hgt_over.json()
        assert data_hgt["is_compatible"] is False
        assert data_hgt["height_clearance_mm"] == 99
        assert any("height clearance" in r.lower() for r in data_hgt["rejection_reasons"])
        assert not any("length" in r.lower() for r in data_hgt["rejection_reasons"])
        assert not any("width" in r.lower() for r in data_hgt["rejection_reasons"])

        # Case E: Triple overflow (1mm over on length, width, and height simultaneously)
        resp_all_over = await client.post(
            f"/api/v1/spaces/{space.id}/compatibility",
            json={
                "vehicle_category": "SEDAN",
                "vehicle_length_mm": 4701,
                "vehicle_width_mm": 2001,
                "vehicle_height_mm": 1901,
                "is_ev": False,
            },
            headers=headers,
        )
        assert resp_all_over.status_code == 200
        data_all = resp_all_over.json()
        assert data_all["is_compatible"] is False
        assert len(data_all["rejection_reasons"]) == 3


# =============================================================================
# 2. EV Charging Compatibility
# =============================================================================


@pytest.mark.asyncio
async def test_adversarial_ev_charging_compatibility(db_session):
    """Verify complete truth table for EV charging requirement vs non-EV / EV parking bays."""
    owner, headers = await _create_owner(db_session, "adv_ev")
    prop = await _create_property(db_session, owner.id, "EV Matrix Prop")

    # Bay 1: NON-EV bay (5.0m x 2.4m x 2.0m, has_ev_charging=False)
    bay_no_ev = ParkingSpace(
        property_id=prop.id,
        space_label="BAY-CONVENTIONAL",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        length_meters=Decimal("5.00"),
        width_meters=Decimal("2.40"),
        height_clearance_meters=Decimal("2.00"),
        has_ev_charging=False,
        base_hourly_rate_paise=5000,
    )
    # Bay 2: EV bay (5.0m x 2.4m x 2.0m, has_ev_charging=True)
    bay_with_ev = ParkingSpace(
        property_id=prop.id,
        space_label="BAY-EV-CHARGER",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        length_meters=Decimal("5.00"),
        width_meters=Decimal("2.40"),
        height_clearance_meters=Decimal("2.00"),
        has_ev_charging=True,
        base_hourly_rate_paise=7500,
    )
    db_session.add_all([bay_no_ev, bay_with_ev])
    await db_session.commit()
    await db_session.refresh(bay_no_ev)
    await db_session.refresh(bay_with_ev)

    fitting_dims = {
        "vehicle_category": "SEDAN",
        "vehicle_length_mm": 4500,
        "vehicle_width_mm": 1800,
        "vehicle_height_mm": 1500,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Driver requests EV via is_ev=True:
        # Non-EV bay must FAIL
        r1 = await client.post(
            f"/api/v1/spaces/{bay_no_ev.id}/compatibility",
            json={**fitting_dims, "is_ev": True, "driver_requires_ev": False},
            headers=headers,
        )
        assert r1.status_code == 200
        assert r1.json()["is_compatible"] is False
        assert any("charging" in r.lower() or "ev" in r.lower() for r in r1.json()["rejection_reasons"])

        # EV bay must PASS
        r2 = await client.post(
            f"/api/v1/spaces/{bay_with_ev.id}/compatibility",
            json={**fitting_dims, "is_ev": True, "driver_requires_ev": False},
            headers=headers,
        )
        assert r2.status_code == 200
        assert r2.json()["is_compatible"] is True

        # 2. Driver requests EV via driver_requires_ev=True:
        # Non-EV bay must FAIL
        r3 = await client.post(
            f"/api/v1/spaces/{bay_no_ev.id}/compatibility",
            json={**fitting_dims, "is_ev": False, "driver_requires_ev": True},
            headers=headers,
        )
        assert r3.status_code == 200
        assert r3.json()["is_compatible"] is False

        # EV bay must PASS
        r4 = await client.post(
            f"/api/v1/spaces/{bay_with_ev.id}/compatibility",
            json={**fitting_dims, "is_ev": False, "driver_requires_ev": True},
            headers=headers,
        )
        assert r4.status_code == 200
        assert r4.json()["is_compatible"] is True

        # 3. Driver does NOT request EV (ICE vehicle):
        # Non-EV bay must PASS
        r5 = await client.post(
            f"/api/v1/spaces/{bay_no_ev.id}/compatibility",
            json={**fitting_dims, "is_ev": False, "driver_requires_ev": False},
            headers=headers,
        )
        assert r5.status_code == 200
        assert r5.json()["is_compatible"] is True

        # EV bay must PASS (Non-EV vehicle can park in EV bay if driver doesn't require charging)
        r6 = await client.post(
            f"/api/v1/spaces/{bay_with_ev.id}/compatibility",
            json={**fitting_dims, "is_ev": False, "driver_requires_ev": False},
            headers=headers,
        )
        assert r6.status_code == 200
        assert r6.json()["is_compatible"] is True

        # 4. Stored function compatibility check without explicit dimensions
        # Driver requests EV on non-EV bay -> FALSE
        r7 = await client.post(
            f"/api/v1/spaces/{bay_no_ev.id}/compatibility",
            json={"vehicle_category": "SEDAN", "driver_requires_ev": True},
            headers=headers,
        )
        assert r7.status_code == 200
        assert r7.json()["is_compatible"] is False

        # Driver requests EV on EV bay -> TRUE
        r8 = await client.post(
            f"/api/v1/spaces/{bay_with_ev.id}/compatibility",
            json={"vehicle_category": "SEDAN", "driver_requires_ev": True},
            headers=headers,
        )
        assert r8.status_code == 200
        assert r8.json()["is_compatible"] is True

        # Driver does NOT request EV on either bay -> TRUE
        r9 = await client.post(
            f"/api/v1/spaces/{bay_no_ev.id}/compatibility",
            json={"vehicle_category": "SEDAN", "driver_requires_ev": False},
            headers=headers,
        )
        assert r9.status_code == 200
        assert r9.json()["is_compatible"] is True

        r10 = await client.post(
            f"/api/v1/spaces/{bay_with_ev.id}/compatibility",
            json={"vehicle_category": "SEDAN", "driver_requires_ev": False},
            headers=headers,
        )
        assert r10.status_code == 200
        assert r10.json()["is_compatible"] is True


# =============================================================================
# 3. Duplicate Space Labels
# =============================================================================


@pytest.mark.asyncio
async def test_adversarial_duplicate_space_labels(db_session):
    """Verify space_label uniqueness is strictly enforced per-property, but allowed across different properties."""
    owner, headers = await _create_owner(db_session, "adv_dup")
    prop_a = await _create_property(db_session, owner.id, "Property Alpha", lat=12.9716, lon=77.5946)
    prop_b = await _create_property(db_session, owner.id, "Property Beta", lat=12.9800, lon=77.6000)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        bay_payload_1 = {
            "space_label": "BAY-RESERVED-01",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 5.0,
            "width_meters": 2.4,
            "height_clearance_meters": 2.1,
            "base_hourly_rate_paise": 6000,
        }

        # Step 1: Create BAY-RESERVED-01 on Property A -> SUCCEED (201)
        r1 = await client.post(f"/api/v1/properties/{prop_a.id}/spaces", json=bay_payload_1, headers=headers)
        assert r1.status_code == 201, r1.text
        bay_a1_id = r1.json()["id"]

        # Step 2: Attempt duplicate BAY-RESERVED-01 on Property A -> FAIL 409 Conflict
        r2 = await client.post(f"/api/v1/properties/{prop_a.id}/spaces", json=bay_payload_1, headers=headers)
        assert r2.status_code == 409, r2.text
        assert r2.json()["code"] == "DUPLICATE_SPACE_LABEL"

        # Step 3: Create BAY-RESERVED-02 on Property A -> SUCCEED (201)
        bay_payload_2 = {**bay_payload_1, "space_label": "BAY-RESERVED-02"}
        r3 = await client.post(f"/api/v1/properties/{prop_a.id}/spaces", json=bay_payload_2, headers=headers)
        assert r3.status_code == 201
        bay_a2_id = r3.json()["id"]

        # Step 4: Attempt to mutate BAY-RESERVED-02 to duplicate BAY-RESERVED-01 on Property A -> FAIL 409 Conflict
        r4 = await client.put(
            f"/api/v1/spaces/{bay_a2_id}",
            json={"space_label": "BAY-RESERVED-01"},
            headers=headers,
        )
        assert r4.status_code == 409
        assert r4.json()["code"] == "DUPLICATE_SPACE_LABEL"

        # Step 5: Mutate BAY-RESERVED-01 keeping its own label (idempotent update) -> SUCCEED (200)
        r5 = await client.put(
            f"/api/v1/spaces/{bay_a1_id}",
            json={"space_label": "BAY-RESERVED-01", "base_hourly_rate_paise": 6500},
            headers=headers,
        )
        assert r5.status_code == 200
        assert r5.json()["base_hourly_rate_paise"] == 6500

        # Step 6: Create identical space label BAY-RESERVED-01 on Property B -> MUST SUCCEED (201)
        r6 = await client.post(f"/api/v1/properties/{prop_b.id}/spaces", json=bay_payload_1, headers=headers)
        assert r6.status_code == 201
        assert r6.json()["space_label"] == "BAY-RESERVED-01"
        assert r6.json()["property_id"] == str(prop_b.id)


# =============================================================================
# 4. Operating Hours Overlap
# =============================================================================


@pytest.mark.asyncio
async def test_adversarial_operating_hours_overlap(db_session):
    """Verify operating schedules prevent overlapping windows on the same day while allowing abutting/disjoint windows."""
    owner, headers = await _create_owner(db_session, "adv_sched")
    prop = await _create_property(db_session, owner.id, "Operating Hours Matrix Prop")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Base window on Day 1 (Monday, day_of_week=0): 09:00:00 to 12:00:00
        r_base = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
            headers=headers,
        )
        assert r_base.status_code == 201, r_base.text

        # Overlap Test 1: Partial overlap end (11:00 to 15:00) -> MUST FAIL 409
        r_ov1 = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 0, "start_time": "11:00:00", "end_time": "15:00:00"},
            headers=headers,
        )
        assert r_ov1.status_code == 409
        assert r_ov1.json()["code"] == "SCHEDULE_OVERLAP_CONFLICT"

        # Overlap Test 2: Partial overlap start (08:00 to 10:00) -> MUST FAIL 409
        r_ov2 = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 0, "start_time": "08:00:00", "end_time": "10:00:00"},
            headers=headers,
        )
        assert r_ov2.status_code == 409
        assert r_ov2.json()["code"] == "SCHEDULE_OVERLAP_CONFLICT"

        # Overlap Test 3: Strict subset inside base window (09:30 to 11:30) -> MUST FAIL 409
        r_ov3 = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 0, "start_time": "09:30:00", "end_time": "11:30:00"},
            headers=headers,
        )
        assert r_ov3.status_code == 409
        assert r_ov3.json()["code"] == "SCHEDULE_OVERLAP_CONFLICT"

        # Overlap Test 4: Strict superset encompassing base window (08:00 to 13:00) -> MUST FAIL 409
        r_ov4 = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 0, "start_time": "08:00:00", "end_time": "13:00:00"},
            headers=headers,
        )
        assert r_ov4.status_code == 409
        assert r_ov4.json()["code"] == "SCHEDULE_OVERLAP_CONFLICT"

        # Overlap Test 5: Exact duplicate (09:00 to 12:00) -> MUST FAIL 409
        r_ov5 = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
            headers=headers,
        )
        assert r_ov5.status_code == 409
        assert r_ov5.json()["code"] == "SCHEDULE_OVERLAP_CONFLICT"

        # Non-Overlapping Test 6: Abutting boundary preceding (08:00 to 09:00) -> MUST SUCCEED (201)
        r_ab_before = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 0, "start_time": "08:00:00", "end_time": "09:00:00"},
            headers=headers,
        )
        assert r_ab_before.status_code == 201

        # Non-Overlapping Test 7: Abutting boundary succeeding (12:00 to 13:00) -> MUST SUCCEED (201)
        r_ab_after = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 0, "start_time": "12:00:00", "end_time": "13:00:00"},
            headers=headers,
        )
        assert r_ab_after.status_code == 201

        # Non-Overlapping Test 8: Disjoint afternoon window (14:00 to 18:00) on same day -> MUST SUCCEED (201)
        r_disjoint = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 0, "start_time": "14:00:00", "end_time": "18:00:00"},
            headers=headers,
        )
        assert r_disjoint.status_code == 201

        # Non-Overlapping Test 9: Identical time (09:00 to 12:00) on a DIFFERENT day (Tuesday, day_of_week=1) -> MUST SUCCEED (201)
        r_diff_day = await client.post(
            f"/api/v1/properties/{prop.id}/operating-hours",
            json={"day_of_week": 1, "start_time": "09:00:00", "end_time": "12:00:00"},
            headers=headers,
        )
        assert r_diff_day.status_code == 201


# =============================================================================
# 5. Blackout Schedule Collision Matrix
# =============================================================================


@pytest.mark.asyncio
async def test_adversarial_blackout_schedule_collisions(db_session):
    """Verify blackout collisions against active blackouts (exact match, subset, superset, touching start/end, abutting)."""
    owner, headers = await _create_owner(db_session, "adv_blackout")
    prop = await _create_property(db_session, owner.id, "Blackout Matrix Prop")

    space = ParkingSpace(
        property_id=prop.id,
        space_label="BAY-BLACKOUT-01",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        length_meters=Decimal("5.00"),
        width_meters=Decimal("2.40"),
        height_clearance_meters=Decimal("2.10"),
        has_ev_charging=False,
        base_hourly_rate_paise=5000,
    )
    db_session.add(space)
    await db_session.commit()
    await db_session.refresh(space)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Base blackout: Dec 10 10:00 to 16:00
        r_base = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={
                "start_time": "2026-12-10T10:00:00Z",
                "end_time": "2026-12-10T16:00:00Z",
                "reason": "Base blackout window",
            },
            headers=headers,
        )
        assert r_base.status_code == 201, r_base.text

        # 1. Exact match (10:00 to 16:00) -> MUST FAIL 409
        r1 = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={"start_time": "2026-12-10T10:00:00Z", "end_time": "2026-12-10T16:00:00Z"},
            headers=headers,
        )
        assert r1.status_code == 409
        assert r1.json()["code"] == "BLACKOUT_OVERLAP_CONFLICT"

        # 2. Strict subset (11:00 to 15:00) -> MUST FAIL 409
        r2 = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={"start_time": "2026-12-10T11:00:00Z", "end_time": "2026-12-10T15:00:00Z"},
            headers=headers,
        )
        assert r2.status_code == 409
        assert r2.json()["code"] == "BLACKOUT_OVERLAP_CONFLICT"

        # 3. Strict superset (09:00 to 17:00) -> MUST FAIL 409
        r3 = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={"start_time": "2026-12-10T09:00:00Z", "end_time": "2026-12-10T17:00:00Z"},
            headers=headers,
        )
        assert r3.status_code == 409
        assert r3.json()["code"] == "BLACKOUT_OVERLAP_CONFLICT"

        # 4. Touching/overlapping start (09:00 to 11:00) -> MUST FAIL 409
        r4 = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={"start_time": "2026-12-10T09:00:00Z", "end_time": "2026-12-10T11:00:00Z"},
            headers=headers,
        )
        assert r4.status_code == 409
        assert r4.json()["code"] == "BLACKOUT_OVERLAP_CONFLICT"

        # 5. Touching/overlapping end (15:00 to 17:00) -> MUST FAIL 409
        r5 = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={"start_time": "2026-12-10T15:00:00Z", "end_time": "2026-12-10T17:00:00Z"},
            headers=headers,
        )
        assert r5.status_code == 409
        assert r5.json()["code"] == "BLACKOUT_OVERLAP_CONFLICT"

        # 6. Abutting boundary before (08:00 to 10:00) -> MUST SUCCEED (201)
        r6 = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={"start_time": "2026-12-10T08:00:00Z", "end_time": "2026-12-10T10:00:00Z"},
            headers=headers,
        )
        assert r6.status_code == 201

        # 7. Abutting boundary after (16:00 to 18:00) -> MUST SUCCEED (201)
        r7 = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={"start_time": "2026-12-10T16:00:00Z", "end_time": "2026-12-10T18:00:00Z"},
            headers=headers,
        )
        assert r7.status_code == 201

        # 8. Property-wide blackout collision with bay-specific blackout
        # Bay has blackout 10:00 to 16:00. Attempt property-wide blackout 12:00 to 14:00 -> MUST FAIL 409
        r8 = await client.post(
            f"/api/v1/properties/{prop.id}/blackouts",
            json={"start_time": "2026-12-10T12:00:00Z", "end_time": "2026-12-10T14:00:00Z"},
            headers=headers,
        )
        assert r8.status_code == 409
        assert r8.json()["code"] == "BLACKOUT_OVERLAP_CONFLICT"

        # 9. Create property-wide blackout Dec 12 20:00 to Dec 12 23:00 -> 201
        r9_prop = await client.post(
            f"/api/v1/properties/{prop.id}/blackouts",
            json={"start_time": "2026-12-12T20:00:00Z", "end_time": "2026-12-12T23:00:00Z"},
            headers=headers,
        )
        assert r9_prop.status_code == 201

        # Bay-specific blackout attempting to overlap property-wide blackout Dec 12 21:00 to 22:00 -> MUST FAIL 409
        r9_bay = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={"start_time": "2026-12-12T21:00:00Z", "end_time": "2026-12-12T22:00:00Z"},
            headers=headers,
        )
        assert r9_bay.status_code == 409
        assert r9_bay.json()["code"] == "BLACKOUT_OVERLAP_CONFLICT"


@pytest.mark.asyncio
async def test_adversarial_blackout_reservation_collision_matrix(db_session):
    """Verify blackout creation collisions against driver reservations (CONFIRMED, ACTIVE_HOLD, CANCELLED)."""
    owner, headers = await _create_owner(db_session, "adv_resv_col")
    prop = await _create_property(db_session, owner.id, "Reservation Collision Prop")

    space = ParkingSpace(
        property_id=prop.id,
        space_label="BAY-RESV-COL-01",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        length_meters=Decimal("5.00"),
        width_meters=Decimal("2.40"),
        height_clearance_meters=Decimal("2.10"),
        has_ev_charging=False,
        base_hourly_rate_paise=5000,
    )
    db_session.add(space)
    await db_session.commit()
    await db_session.refresh(space)

    # Insert a vehicle for reservation tests
    veh_id = uuid.uuid4()
    conn = await db_session.connection()
    raw_conn = await conn.get_raw_connection()
    await raw_conn.driver_connection.execute(
        """
        INSERT INTO vehicles (id, driver_id, registration_plate, vehicle_category)
        VALUES ($1, $2, $3, 'SEDAN')
        """,
        veh_id,
        owner.id,
        f"KA01AB{secrets.token_hex(2).upper()}",
    )

    # Helper to insert space_reservations row directly
    async def _insert_reservation(resv_id: uuid.UUID, start_iso: str, end_iso: str, status: str):
        st = datetime.fromisoformat(start_iso)
        et = datetime.fromisoformat(end_iso)
        time_window = asyncpg.Range(st, et, lower_inc=True, upper_inc=False)
        hold_exp = (datetime.now(timezone.utc) + timedelta(minutes=15)) if status == "ACTIVE_HOLD" else None
        conn = await db_session.connection()
        raw = await conn.get_raw_connection()
        await raw.driver_connection.execute(
            """
            INSERT INTO space_reservations (
                id, parking_space_id, driver_id, vehicle_id,
                time_window, reservation_type, status, booking_reference, hold_expires_at
            ) VALUES (
                $1, $2, $3, $4,
                $5, 'CONFIRMED_BOOKING', CAST($6 AS reservation_status_enum), $7, $8
            )
            """,
            resv_id,
            space.id,
            owner.id,
            veh_id,
            time_window,
            status,
            f"BK-{secrets.token_hex(4).upper()}",
            hold_exp,
        )
        await db_session.commit()

    # 1. Insert CONFIRMED reservation: Dec 20 10:00 to 14:00
    resv_conf_id = uuid.uuid4()
    await _insert_reservation(resv_conf_id, "2026-12-20T10:00:00+00:00", "2026-12-20T14:00:00+00:00", "CONFIRMED")

    # 2. Insert ACTIVE_HOLD reservation: Dec 21 10:00 to 14:00
    resv_hold_id = uuid.uuid4()
    await _insert_reservation(resv_hold_id, "2026-12-21T10:00:00+00:00", "2026-12-21T14:00:00+00:00", "ACTIVE_HOLD")

    # 3. Insert CANCELLED reservation: Dec 22 10:00 to 14:00
    resv_canc_id = uuid.uuid4()
    await _insert_reservation(resv_canc_id, "2026-12-22T10:00:00+00:00", "2026-12-22T14:00:00+00:00", "CANCELLED_BY_DRIVER")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # A. Blackout overlapping CONFIRMED reservation (Dec 20 11:00 to 13:00) -> MUST FAIL 409
        r_conf_col = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={"start_time": "2026-12-20T11:00:00Z", "end_time": "2026-12-20T13:00:00Z"},
            headers=headers,
        )
        assert r_conf_col.status_code == 409
        assert r_conf_col.json()["code"] == "RESERVATION_OVERLAP_CONFLICT"

        # B. Blackout overlapping ACTIVE_HOLD reservation (Dec 21 09:00 to 12:00) -> MUST FAIL 409
        r_hold_col = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={"start_time": "2026-12-21T09:00:00Z", "end_time": "2026-12-21T12:00:00Z"},
            headers=headers,
        )
        assert r_hold_col.status_code == 409
        assert r_hold_col.json()["code"] == "RESERVATION_OVERLAP_CONFLICT"

        # C. Blackout overlapping CANCELLED reservation (Dec 22 11:00 to 13:00) -> MUST SUCCEED (201)
        r_canc_ok = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={"start_time": "2026-12-22T11:00:00Z", "end_time": "2026-12-22T13:00:00Z"},
            headers=headers,
        )
        assert r_canc_ok.status_code == 201

        # D. Blackout strictly before CONFIRMED reservation (Dec 20 08:00 to 10:00) -> MUST SUCCEED (201)
        r_before_ok = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={"start_time": "2026-12-20T08:00:00Z", "end_time": "2026-12-20T10:00:00Z"},
            headers=headers,
        )
        assert r_before_ok.status_code == 201

        # E. Blackout strictly after CONFIRMED reservation (Dec 20 14:00 to 16:00) -> MUST SUCCEED (201)
        r_after_ok = await client.post(
            f"/api/v1/spaces/{space.id}/blackouts",
            json={"start_time": "2026-12-20T14:00:00Z", "end_time": "2026-12-20T16:00:00Z"},
            headers=headers,
        )
        assert r_after_ok.status_code == 201
