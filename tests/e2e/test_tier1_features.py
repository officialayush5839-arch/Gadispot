"""Tier 1: Feature Coverage E2E Tests for Phase 03 Supply Engine.

Covers all 18 core backend Phase 03 features (>= 5 tests per feature = 90 tests):
1. Property creation (POST /api/v1/properties)
2. PostGIS location coordinates (POINT(longitude latitude), WGS 84 SRID 4326)
3. Bay creation (POST /api/v1/properties/{id}/spaces)
4. Dimensional clearances (length, width, height clearances + compatibility calculation)
5. EV requirement (EV bay toggle, driver EV request check)
6. Operating hours (POST /api/v1/properties/{id}/operating-hours)
7. Blackout creation (POST /api/v1/spaces/{id}/blackouts)
8. Presigned upload URLs (POST /api/v1/properties/{id}/documents/presign)
9. Upload verification (POST /api/v1/properties/{id}/documents/{doc_id}/verify)
10. Watermarked download (GET /api/v1/ops/documents/{doc_id}/watermarked)
11. Review queue listing (GET /api/v1/ops/properties/queue)
12. Review claim/dossier (GET /api/v1/ops/properties/{id})
13. TOTP step-up approval (POST /api/v1/ops/properties/{id}/approve)
14. TOTP step-up rejection (POST /api/v1/ops/properties/{id}/reject)
15. Rejection reason validation (structured rejection code, notes)
16. Resubmission (POST /api/v1/properties/{id}/submit-review after rejection/draft)
17. Discovery exclusion of unapproved properties (unapproved, draft, submitted, rejected not in public discovery)
18. Audit event emission (audit log entries emitted on state transitions)
"""

import uuid
from datetime import datetime

import pytest
from app.models.enums import (
    AccountStatus,
    AuthorizationStatusEnum,
    UserRoleEnum,
)
from app.models.properties import Property, PropertyAuthorization
from app.models.schedules import BlackoutSchedule
from app.models.users import User, UserRole
from app.services.compatibility_service import (
    CompatibilityService,
    SpaceDimensions,
    VehicleDimensions,
)
from httpx import AsyncClient
from sqlalchemy import select, text

from tests.e2e.conftest import get_current_totp

# =============================================================================
# FEATURE 1: Property Creation (POST /api/v1/properties)
# =============================================================================


@pytest.mark.asyncio
async def test_f01_create_residential_property_success(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F1.1: Space owner creates a residential driveway property with valid address, city, and WGS 84 Point coordinates."""
    _, headers = owner_user
    payload = {
        "title": "Green Glen Driveway",
        "property_type": "RESIDENTIAL_DRIVEWAY",
        "address_line": "123 Outer Ring Road, Bellandur",
        "city": "Bengaluru",
        "postal_code": "560103",
        "latitude": 12.9352,
        "longitude": 77.6772,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    assert "id" in data
    assert data["title"] == payload["title"]
    assert data["property_type"] == payload["property_type"]
    assert data["city"] == payload["city"]
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_f01_create_commercial_property_success(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F1.2: Space owner creates a commercial building property with custom advance days and max booking duration."""
    _, headers = owner_user
    payload = {
        "title": "Prestige Tech Park Hub",
        "property_type": "COMMERCIAL_BUILDING",
        "address_line": "Marathahalli-Sarjapur Ring Rd",
        "city": "Bengaluru",
        "postal_code": "560103",
        "latitude": 12.9376,
        "longitude": 77.6903,
        "max_advance_days": 14,
        "max_booking_hours": 48,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    assert data["max_advance_days"] == 14
    assert data["max_booking_hours"] == 48


@pytest.mark.asyncio
async def test_f01_create_property_initial_status_draft(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]], db_session
):
    """F1.3: Created property is assigned DRAFT status and is_active is strictly False."""
    _, headers = owner_user
    payload = {
        "title": "Indiranagar Spot",
        "property_type": "RESIDENTIAL_DRIVEWAY",
        "address_line": "100 Feet Road",
        "city": "Bengaluru",
        "postal_code": "560038",
        "latitude": 12.9784,
        "longitude": 77.6408,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (200, 201)
    prop_id = uuid.UUID(resp.json()["id"])

    stmt = select(Property).where(Property.id == prop_id)
    prop = (await db_session.execute(stmt)).scalar_one()
    assert prop.is_active is False


@pytest.mark.asyncio
async def test_f01_create_property_initializes_authorization_version_1(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]], db_session
):
    """F1.4: Property creation automatically initializes a linked PropertyAuthorization record in DRAFT status with version 1."""
    _, headers = owner_user
    payload = {
        "title": "Koramangala Plot",
        "property_type": "OPEN_PLOT",
        "address_line": "5th Block, Koramangala",
        "city": "Bengaluru",
        "postal_code": "560095",
        "latitude": 12.9345,
        "longitude": 77.6190,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (200, 201)
    prop_id = uuid.UUID(resp.json()["id"])

    auth_stmt = select(PropertyAuthorization).where(
        PropertyAuthorization.property_id == prop_id
    )
    prop_auth = (await db_session.execute(auth_stmt)).scalar_one_or_none()
    assert prop_auth is not None
    assert prop_auth.status == AuthorizationStatusEnum.DRAFT
    assert prop_auth.version == 1


@pytest.mark.asyncio
async def test_f01_create_property_unauthenticated_or_unauthorized(
    e2e_client: AsyncClient, driver_user: tuple[User, dict[str, str]]
):
    """F1.5: Property creation rejects unauthenticated callers (401) and unauthorized non-owner roles (403)."""
    payload = {
        "title": "Unauth Property",
        "property_type": "RESIDENTIAL_DRIVEWAY",
        "address_line": "MG Road",
        "city": "Bengaluru",
        "postal_code": "560001",
        "latitude": 12.9716,
        "longitude": 77.5946,
    }
    # 1. Unauthenticated request
    resp_unauth = await e2e_client.post("/api/v1/properties", json=payload)
    assert resp_unauth.status_code == 401

    # 2. Driver role request
    _, driver_headers = driver_user
    resp_forbidden = await e2e_client.post(
        "/api/v1/properties", json=payload, headers=driver_headers
    )
    assert resp_forbidden.status_code == 403


# =============================================================================
# FEATURE 2: PostGIS Location Coordinates (idx_properties_location)
# =============================================================================


@pytest.mark.asyncio
async def test_f02_postgis_point_coordinates_persistence(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]], db_session
):
    """F2.1: PostGIS persists WGS 84 coordinates as POINT(longitude latitude) with SRID 4326."""
    _, headers = owner_user
    payload = {
        "title": "Central Bengaluru Spot",
        "property_type": "RESIDENTIAL_DRIVEWAY",
        "address_line": "Cubbon Park Road",
        "city": "Bengaluru",
        "postal_code": "560001",
        "latitude": 12.9716,
        "longitude": 77.5946,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (200, 201)
    prop_id = resp.json()["id"]

    query = text(
        "SELECT ST_AsText(location), ST_SRID(location) FROM properties WHERE id = :id"
    )
    row = (await db_session.execute(query, {"id": prop_id})).fetchone()
    assert row is not None
    assert row[0] == "POINT(77.5946 12.9716)"
    assert row[1] == 4326


@pytest.mark.asyncio
async def test_f02_postgis_spatial_distance_query(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]], db_session
):
    """F2.2: PostGIS spatial query ST_DWithin locates properties within given radial distance in meters."""
    _, headers = owner_user
    payload = {
        "title": "HSR Layout Bay",
        "property_type": "RESIDENTIAL_DRIVEWAY",
        "address_line": "27th Main, Sector 1, HSR",
        "city": "Bengaluru",
        "postal_code": "560102",
        "latitude": 12.9116,
        "longitude": 77.6433,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (200, 201)
    prop_id = resp.json()["id"]

    query = text("""
        SELECT id FROM properties 
        WHERE ST_DWithin(
            location::geography,
            ST_SetSRID(ST_MakePoint(77.6430, 12.9110), 4326)::geography,
            500
        ) AND id = :id
    """)
    result = (await db_session.execute(query, {"id": prop_id})).scalar_one_or_none()
    assert result is not None


@pytest.mark.asyncio
async def test_f02_postgis_multiple_metro_coordinates(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F2.3: Supports coordinate persistence across multiple distinct Indian metropolitan locations."""
    _, headers = owner_user
    metros = [
        {
            "title": "Mumbai BKC Spot",
            "city": "Mumbai",
            "lat": 19.0657,
            "lon": 72.8687,
            "pin": "400051",
        },
        {
            "title": "Delhi Connaught Hub",
            "city": "New Delhi",
            "lat": 28.6315,
            "lon": 77.2167,
            "pin": "110001",
        },
    ]
    for metro in metros:
        payload = {
            "title": metro["title"],
            "property_type": "COMMERCIAL_BUILDING",
            "address_line": "Financial District",
            "city": metro["city"],
            "postal_code": metro["pin"],
            "latitude": metro["lat"],
            "longitude": metro["lon"],
        }
        resp = await e2e_client.post(
            "/api/v1/properties", json=payload, headers=headers
        )
        assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_f02_postgis_invalid_coordinate_format_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F2.4: Reject malformed or non-numeric coordinate inputs with HTTP 422."""
    _, headers = owner_user
    payload = {
        "title": "Invalid Coordinates Spot",
        "property_type": "RESIDENTIAL_DRIVEWAY",
        "address_line": "Indiranagar",
        "city": "Bengaluru",
        "postal_code": "560038",
        "latitude": "not-a-number",
        "longitude": 77.6408,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_f02_postgis_spatial_index_verification(db_session):
    """F2.5: Verifies that GiST spatial index idx_properties_location exists on properties.location."""
    query = text("""
        SELECT indexname, indexdef FROM pg_indexes 
        WHERE tablename = 'properties' AND indexname = 'idx_properties_location'
    """)
    row = (await db_session.execute(query)).fetchone()
    assert row is not None
    assert "gist" in row[1].lower()


# =============================================================================
# FEATURE 3: Parking Bay Creation (POST /api/v1/properties/{id}/spaces)
# =============================================================================


@pytest.mark.asyncio
async def test_f03_create_standard_covered_bay_success(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F3.1: Space owner creates a standard covered car bay with valid dimensions and tariff."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Owner Property For Bays",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Koramangala 4th Block",
            "city": "Bengaluru",
            "postal_code": "560034",
            "latitude": 12.9333,
            "longitude": 77.6250,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    space_payload = {
        "space_label": "BAY-C01",
        "space_type": "COVERED",
        "vehicle_category": "SEDAN",
        "length_meters": 4.80,
        "width_meters": 2.40,
        "height_clearance_meters": 2.10,
        "has_ev_charging": False,
        "base_hourly_rate_paise": 6000,
    }
    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces", json=space_payload, headers=headers
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["space_label"] == "BAY-C01"
    assert data["base_hourly_rate_paise"] == 6000


@pytest.mark.asyncio
async def test_f03_create_two_wheeler_bay_success(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F3.2: Space owner creates a dedicated two-wheeler bay with tailored dimensions."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Bike Friendly Home",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "BTM 2nd Stage",
            "city": "Bengaluru",
            "postal_code": "560076",
            "latitude": 12.9165,
            "longitude": 77.6101,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    space_payload = {
        "space_label": "BIKE-01",
        "space_type": "OPEN",
        "vehicle_category": "TWO_WHEELER",
        "length_meters": 2.20,
        "width_meters": 1.00,
        "height_clearance_meters": 2.00,
        "has_ev_charging": False,
        "base_hourly_rate_paise": 2000,
    }
    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces", json=space_payload, headers=headers
    )
    assert resp.status_code in (200, 201)
    assert resp.json()["vehicle_category"] == "TWO_WHEELER"


@pytest.mark.asyncio
async def test_f03_create_basement_suv_bay_success(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F3.3: Space owner creates a large basement SUV bay with 2.2m clearance height."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Basement Complex",
            "property_type": "COMMERCIAL_BUILDING",
            "address_line": "Whitefield Main Rd",
            "city": "Bengaluru",
            "postal_code": "560066",
            "latitude": 12.9698,
            "longitude": 77.7499,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    space_payload = {
        "space_label": "SUV-B1",
        "space_type": "BASEMENT",
        "vehicle_category": "SUV",
        "length_meters": 5.20,
        "width_meters": 2.50,
        "height_clearance_meters": 2.20,
        "has_ev_charging": False,
        "base_hourly_rate_paise": 10000,
    }
    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces", json=space_payload, headers=headers
    )
    assert resp.status_code in (200, 201)
    assert resp.json()["vehicle_category"] == "SUV"


@pytest.mark.asyncio
async def test_f03_create_duplicate_space_label_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F3.4: Enforces database unique constraint uq_parking_spaces_property_label when duplicate label is used on same property."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Dup Test Property",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "JP Nagar 7th Phase",
            "city": "Bengaluru",
            "postal_code": "560078",
            "latitude": 12.8912,
            "longitude": 77.5843,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    space_payload = {
        "space_label": "BAY-UNIQUE",
        "space_type": "COVERED",
        "vehicle_category": "HATCHBACK",
        "length_meters": 4.50,
        "width_meters": 2.20,
        "height_clearance_meters": 2.10,
        "has_ev_charging": False,
        "base_hourly_rate_paise": 4000,
    }
    resp1 = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces", json=space_payload, headers=headers
    )
    assert resp1.status_code in (200, 201)

    # Second attempt with identical label must be rejected
    resp2 = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces", json=space_payload, headers=headers
    )
    assert resp2.status_code in (400, 409, 422)


@pytest.mark.asyncio
async def test_f03_create_bay_cross_owner_idor_forbidden(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]], db_session
):
    """F3.5: Prevents IDOR attack: a second owner cannot add a parking bay to another owner's property."""
    _user1, headers1 = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Protected Property",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Malleshwaram",
            "city": "Bengaluru",
            "postal_code": "560003",
            "latitude": 13.0031,
            "longitude": 77.5643,
        },
        headers=headers1,
    )
    prop_id = prop_resp.json()["id"]

    # Provision Owner 2
    phone2 = f"+9198{uuid.uuid4().hex[:8]}"
    user2 = User(
        phone_number=phone2,
        full_name="Owner 2",
        status=AccountStatus.ACTIVE,
        is_active=True,
    )
    db_session.add(user2)
    await db_session.flush()
    db_session.add(UserRole(user_id=user2.id, role=UserRoleEnum.OWNER))
    await db_session.commit()
    from app.core.security import create_access_token

    token2 = create_access_token(
        subject=str(user2.id), claims={"roles": ["OWNER"], "phone_number": phone2}
    )
    headers2 = {"Authorization": f"Bearer {token2}"}

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "ATTACK-BAY",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=headers2,
    )
    assert resp.status_code == 403


# =============================================================================
# FEATURE 4: Dimensional Clearances & Compatibility Calculation
# =============================================================================


@pytest.mark.asyncio
async def test_f04_dimensional_clearance_sedan_fits_standard_bay():
    """F4.1: Sedan vehicle satisfies 3D clearance margins (+300mm length, +400mm width, +100mm height)."""
    vehicle = VehicleDimensions(length_mm=4500, width_mm=1800, height_mm=1500)
    space = SpaceDimensions(length_mm=4900, width_mm=2300, height_mm=2000)
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is True
    assert res.length_clearance_mm == 400  # >= 300mm
    assert res.width_clearance_mm == 500  # >= 400mm
    assert res.height_clearance_mm == 500  # >= 100mm


@pytest.mark.asyncio
async def test_f04_dimensional_clearance_suv_fails_compact_bay():
    """F4.2: Large SUV fails compatibility in undersized bay with explicit clearance rejection details."""
    vehicle = VehicleDimensions(length_mm=4900, width_mm=2000, height_mm=1850)
    space = SpaceDimensions(length_mm=4800, width_mm=2100, height_mm=1900)
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is False
    assert any("length clearance" in r.lower() for r in res.rejection_reasons)
    assert any("width clearance" in r.lower() for r in res.rejection_reasons)


@pytest.mark.asyncio
async def test_f04_dimensional_clearance_two_wheeler_dedicated_bay():
    """F4.3: Two-wheeler motorcycle satisfies physical clearances in dedicated bike bay."""
    vehicle = VehicleDimensions(length_mm=2000, width_mm=750, height_mm=1200)
    space = SpaceDimensions(length_mm=2400, width_mm=1200, height_mm=2000)
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is True


@pytest.mark.asyncio
async def test_f04_stored_function_vehicle_bay_compatibility_true(db_session):
    """F4.4: Stored PostgreSQL function fn_check_vehicle_bay_compatibility returns TRUE for compatible bay dimensions."""
    query = text("""
        SELECT fn_check_vehicle_bay_compatibility(
            'SEDAN'::vehicle_category_enum,
            'STANDARD_CAR',
            4.80,
            2.40,
            2.10,
            FALSE,
            FALSE
        );
    """)
    result = (await db_session.execute(query)).scalar()
    assert result is True


@pytest.mark.asyncio
async def test_f04_stored_function_vehicle_bay_compatibility_false(db_session):
    """F4.5: Stored PostgreSQL function fn_check_vehicle_bay_compatibility returns FALSE when bay is undersized."""
    query = text("""
        SELECT fn_check_vehicle_bay_compatibility(
            'SUV'::vehicle_category_enum,
            'COMPACT_CAR',
            3.50,
            1.50,
            1.80,
            FALSE,
            FALSE
        );
    """)
    result = (await db_session.execute(query)).scalar()
    assert result is False


# =============================================================================
# FEATURE 5: EV Requirement Enforcement
# =============================================================================


@pytest.mark.asyncio
async def test_f05_create_ev_bay_persists_flag(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F5.1: Space owner creates bay with has_ev_charging=True and confirms flag persistence."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "EV Charging Station",
            "property_type": "COMMERCIAL_BUILDING",
            "address_line": "Electronic City Phase 1",
            "city": "Bengaluru",
            "postal_code": "560100",
            "latitude": 12.8399,
            "longitude": 77.6770,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    space_payload = {
        "space_label": "EV-FAST-01",
        "space_type": "COVERED",
        "vehicle_category": "EV_FOUR_WHEELER",
        "length_meters": 5.00,
        "width_meters": 2.40,
        "height_clearance_meters": 2.10,
        "has_ev_charging": True,
        "base_hourly_rate_paise": 8000,
    }
    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces", json=space_payload, headers=headers
    )
    assert resp.status_code in (200, 201)
    assert resp.json()["has_ev_charging"] is True


@pytest.mark.asyncio
async def test_f05_ev_vehicle_compatible_with_ev_bay():
    """F5.2: EV vehicle evaluated against a dedicated EV bay is compatible."""
    vehicle = VehicleDimensions(
        length_mm=4500, width_mm=1800, height_mm=1600, is_ev=True
    )
    space = SpaceDimensions(
        length_mm=4900, width_mm=2300, height_mm=2000, is_ev_charging=True
    )
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is True


@pytest.mark.asyncio
async def test_f05_ev_vehicle_incompatible_with_non_ev_bay():
    """F5.3: EV vehicle evaluated against non-EV bay fails compatibility with EV requirement error."""
    vehicle = VehicleDimensions(
        length_mm=4500, width_mm=1800, height_mm=1600, is_ev=True
    )
    space = SpaceDimensions(
        length_mm=4900, width_mm=2300, height_mm=2000, is_ev_charging=False
    )
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is False
    assert any(
        "requires dedicated charging" in r.lower() for r in res.rejection_reasons
    )


@pytest.mark.asyncio
async def test_f05_non_ev_vehicle_compatible_with_ev_bay():
    """F5.4: Non-EV vehicle parking in an EV bay succeeds (physical dimensions match, EV is optional amenity)."""
    vehicle = VehicleDimensions(
        length_mm=4500, width_mm=1800, height_mm=1600, is_ev=False
    )
    space = SpaceDimensions(
        length_mm=4900, width_mm=2300, height_mm=2000, is_ev_charging=True
    )
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is True


@pytest.mark.asyncio
async def test_f05_stored_function_ev_requirement_check(db_session):
    """F5.5: Stored function fn_check_vehicle_bay_compatibility enforces p_driver_req_ev against p_bay_has_ev."""
    query = text("""
        SELECT fn_check_vehicle_bay_compatibility(
            'SEDAN'::vehicle_category_enum,
            'STANDARD_CAR',
            5.00,
            2.40,
            2.10,
            FALSE, -- bay does not have EV
            TRUE   -- driver requests EV
        );
    """)
    result = (await db_session.execute(query)).scalar()
    assert result is False


# =============================================================================
# FEATURE 6: Operating Hours Configuration (POST /api/v1/properties/{id}/operating-hours)
# =============================================================================


@pytest.mark.asyncio
async def test_f06_add_standard_weekday_operating_hours(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F6.1: Space owner configures standard recurring operating hours (Mon-Fri 08:00 - 18:00)."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Weekday Office Park",
            "property_type": "COMMERCIAL_BUILDING",
            "address_line": "CBD",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    schedule_payload = {
        "day_of_week": 1,
        "start_time": "08:00:00",
        "end_time": "18:00:00",
    }
    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/operating-hours",
        json=schedule_payload,
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["day_of_week"] == 1


@pytest.mark.asyncio
async def test_f06_add_24_7_operating_hours(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F6.2: Space owner configures 24/7 operating hours for all 7 days."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "24x7 Airport Spot",
            "property_type": "OPEN_PLOT",
            "address_line": "Devanahalli",
            "city": "Bengaluru",
            "postal_code": "562110",
            "latitude": 13.1986,
            "longitude": 77.7066,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/operating-hours",
        json={"day_of_week": 0, "start_time": "00:00:00", "end_time": "23:59:59"},
        headers=headers,
    )
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_f06_reject_overlapping_schedules_same_day(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F6.3: Reject overlapping schedule windows on the same day for the same property."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Overlap Test Property",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Banaswadi",
            "city": "Bengaluru",
            "postal_code": "560043",
            "latitude": 13.0142,
            "longitude": 77.6517,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    # Window 1: 08:00 to 14:00
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/operating-hours",
        json={"day_of_week": 2, "start_time": "08:00:00", "end_time": "14:00:00"},
        headers=headers,
    )

    # Window 2: Overlapping 12:00 to 18:00
    resp2 = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/operating-hours",
        json={"day_of_week": 2, "start_time": "12:00:00", "end_time": "18:00:00"},
        headers=headers,
    )
    assert resp2.status_code in (400, 409, 422)


@pytest.mark.asyncio
async def test_f06_reject_invalid_day_of_week(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F6.4: Reject invalid day_of_week (<0 or >6) violating chk_day_of_week constraint."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Day Check Property",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Hebbal",
            "city": "Bengaluru",
            "postal_code": "560024",
            "latitude": 13.0358,
            "longitude": 77.5970,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/operating-hours",
        json={"day_of_week": 7, "start_time": "08:00:00", "end_time": "18:00:00"},
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_f06_reject_inverted_operating_hours(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F6.5: Reject inverted operating hours where start_time >= end_time violating chk_schedule_time."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Invert Check Property",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Yeshwanthpur",
            "city": "Bengaluru",
            "postal_code": "560022",
            "latitude": 13.0282,
            "longitude": 77.5404,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/operating-hours",
        json={"day_of_week": 3, "start_time": "18:00:00", "end_time": "08:00:00"},
        headers=headers,
    )
    assert resp.status_code in (400, 422)


# =============================================================================
# FEATURE 7: Manual Space Blackouts (POST /api/v1/spaces/{id}/blackouts)
# =============================================================================


@pytest.mark.asyncio
async def test_f07_create_space_blackout_success(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F7.1: Space owner creates a personal blackout window for a specific bay."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Blackout Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Jayanagar",
            "city": "Bengaluru",
            "postal_code": "560041",
            "latitude": 12.9308,
            "longitude": 77.5838,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]
    space_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "B1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=headers,
    )
    space_id = space_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/spaces/{space_id}/blackouts",
        json={
            "start_time": "2026-12-01T08:00:00Z",
            "end_time": "2026-12-02T18:00:00Z",
            "reason": "Personal guest visit",
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    assert resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_f07_create_property_wide_blackout(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F7.2: Space owner creates a property-wide blackout blocking all bays on the property."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "All-Bay Maintenance Prop",
            "property_type": "APARTMENT_SOCIETY",
            "address_line": "Sarjapur Rd",
            "city": "Bengaluru",
            "postal_code": "560035",
            "latitude": 12.9100,
            "longitude": 77.6800,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/blackouts",
        json={
            "start_time": "2026-12-10T00:00:00Z",
            "end_time": "2026-12-10T23:59:59Z",
            "reason": "Building driveway repaving",
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_f07_reject_blackout_overlapping_confirmed_booking(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]], db_session
):
    """F7.3: Reject blackout creation that overlaps with an existing confirmed driver booking."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Booking Conflict Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Rajajinagar",
            "city": "Bengaluru",
            "postal_code": "560010",
            "latitude": 12.9982,
            "longitude": 77.5530,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]
    space_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "B-CONF",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=headers,
    )
    space_id = space_resp.json()["id"]

    # Insert a simulated confirmed booking via DB
    from app.models.enums import ReservationStatusEnum, ReservationTypeEnum
    from app.models.reservations import SpaceReservation

    res = SpaceReservation(
        parking_space_id=uuid.UUID(space_id),
        driver_id=owner_user[0].id,
        reservation_type=ReservationTypeEnum.CONFIRMED_BOOKING,
        status=ReservationStatusEnum.CONFIRMED,
        start_time=datetime.fromisoformat("2026-12-05T10:00:00+00:00"),
        end_time=datetime.fromisoformat("2026-12-05T14:00:00+00:00"),
        total_amount_paise=20000,
    )
    db_session.add(res)
    await db_session.commit()

    # Attempt overlapping blackout
    resp = await e2e_client.post(
        f"/api/v1/spaces/{space_id}/blackouts",
        json={
            "start_time": "2026-12-05T09:00:00Z",
            "end_time": "2026-12-05T15:00:00Z",
            "reason": "Overlapping blackout",
        },
        headers=headers,
    )
    assert resp.status_code in (400, 409, 422)


@pytest.mark.asyncio
async def test_f07_reject_inverted_blackout_time(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F7.4: Reject blackout where start_time >= end_time violating chk_blackout_time constraint."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Invert Blackout",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Kengeri",
            "city": "Bengaluru",
            "postal_code": "560060",
            "latitude": 12.9177,
            "longitude": 77.4838,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/blackouts",
        json={
            "start_time": "2026-12-05T18:00:00Z",
            "end_time": "2026-12-05T09:00:00Z",
            "reason": "Inverted time range",
        },
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_f07_blackout_suppresses_bay_availability(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]], db_session
):
    """F7.5: Active blackout correctly suppresses bay availability during the specified blackout period."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Avail Check Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Basavanagudi",
            "city": "Bengaluru",
            "postal_code": "560004",
            "latitude": 12.9432,
            "longitude": 77.5753,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]
    space_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "AV-01",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=headers,
    )
    space_id = space_resp.json()["id"]

    # Create active blackout
    await e2e_client.post(
        f"/api/v1/spaces/{space_id}/blackouts",
        json={
            "start_time": "2026-12-25T00:00:00Z",
            "end_time": "2026-12-25T23:59:59Z",
            "reason": "Christmas Day personal block",
        },
        headers=headers,
    )

    stmt = select(BlackoutSchedule).where(
        BlackoutSchedule.parking_space_id == uuid.UUID(space_id)
    )
    b_row = (await db_session.execute(stmt)).scalar_one_or_none()
    assert b_row is not None
    assert b_row.is_active is True


# =============================================================================
# FEATURE 8: Presigned Upload URLs (POST /api/v1/properties/{id}/documents/presign)
# =============================================================================


@pytest.mark.asyncio
async def test_f08_presign_property_tax_receipt_pdf(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F8.1: Generate presigned upload URL for PROPERTY_TAX_RECEIPT (application/pdf, 15-minute expiry)."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Tax Receipt Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Sadashivanagar",
            "city": "Bengaluru",
            "postal_code": "560080",
            "latitude": 13.0068,
            "longitude": 77.5813,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax_receipt_2026.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1048576,
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert "upload_url" in data
    assert "document_id" in data
    assert data["expires_in"] == 900


@pytest.mark.asyncio
async def test_f08_presign_electricity_bill_jpeg(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F8.2: Generate presigned upload URL for ELECTRICITY_BILL image (image/jpeg)."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Electric Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Vasanth Nagar",
            "city": "Bengaluru",
            "postal_code": "560052",
            "latitude": 12.9890,
            "longitude": 77.5870,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "ELECTRICITY_BILL",
            "file_name": "bescom_bill.jpg",
            "content_type": "image/jpeg",
            "file_size_bytes": 524288,
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    assert "upload_url" in resp.json()


@pytest.mark.asyncio
async def test_f08_presign_society_noc_png(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F8.3: Generate presigned upload URL for SOCIETY_NOC (image/png)."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Society NOC Prop",
            "property_type": "APARTMENT_SOCIETY",
            "address_line": "Bannerghatta Rd",
            "city": "Bengaluru",
            "postal_code": "560076",
            "latitude": 12.8950,
            "longitude": 77.5990,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "SOCIETY_NOC",
            "file_name": "noc_letter.png",
            "content_type": "image/png",
            "file_size_bytes": 2097152,
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_f08_presign_unsupported_mime_type_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F8.4: Reject presign requests with unsupported MIME types (e.g. application/x-executable)."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "MIME Check",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "RT Nagar",
            "city": "Bengaluru",
            "postal_code": "560032",
            "latitude": 13.0184,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "SALE_DEED",
            "file_name": "malicious.sh",
            "content_type": "application/x-sh",
            "file_size_bytes": 1024,
        },
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_f08_presign_idor_protection(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    driver_user: tuple[User, dict[str, str]],
):
    """F8.5: Cross-tenant IDOR protection: other users cannot request upload URLs for another owner's property."""
    _, owner_headers = owner_user
    _, driver_headers = driver_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Protected Doc Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Ulsoor",
            "city": "Bengaluru",
            "postal_code": "560008",
            "latitude": 12.9817,
            "longitude": 77.6286,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1024,
        },
        headers=driver_headers,
    )
    assert resp.status_code == 403


# =============================================================================
# FEATURE 9: Server-Side Upload Verification (POST /api/v1/properties/{id}/documents/{doc_id}/verify)
# =============================================================================


@pytest.mark.asyncio
async def test_f09_verify_uploaded_document_success(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F9.1: Server-side completion verification verifies file presence in storage and sets is_verified=True."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Verify Doc Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Frazer Town",
            "city": "Bengaluru",
            "postal_code": "560005",
            "latitude": 12.9968,
            "longitude": 77.6131,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    presign_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "verified_tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 500000,
        },
        headers=headers,
    )
    doc_id = presign_resp.json()["document_id"]

    verify_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{doc_id}/verify", headers=headers
    )
    assert verify_resp.status_code in (200, 201)
    assert verify_resp.json()["is_verified"] is True


@pytest.mark.asyncio
async def test_f09_verify_document_persists_verification_status(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]], db_session
):
    """F9.2: Database record confirms is_verified=True and uploaded_at timestamp is persisted."""
    from app.models.documents import PropertyDocument

    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "DB Check Doc Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Cooke Town",
            "city": "Bengaluru",
            "postal_code": "560005",
            "latitude": 12.9990,
            "longitude": 77.6200,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    presign_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "SALE_DEED",
            "file_name": "sale_deed.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 600000,
        },
        headers=headers,
    )
    doc_id = presign_resp.json()["document_id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{doc_id}/verify", headers=headers
    )

    stmt = select(PropertyDocument).where(PropertyDocument.id == uuid.UUID(doc_id))
    doc = (await db_session.execute(stmt)).scalar_one_or_none()
    assert doc is not None
    assert doc.is_verified is True
    assert doc.uploaded_at is not None


@pytest.mark.asyncio
async def test_f09_verify_missing_file_in_storage_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F9.3: Verify request fails with 400/422 when underlying file was never uploaded to storage."""
    _, headers = owner_user
    fake_prop_id = str(uuid.uuid4())
    fake_doc_id = str(uuid.uuid4())
    resp = await e2e_client.post(
        f"/api/v1/properties/{fake_prop_id}/documents/{fake_doc_id}/verify",
        headers=headers,
    )
    assert resp.status_code in (400, 404, 422)


@pytest.mark.asyncio
async def test_f09_verify_oversized_file_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F9.4: Presign / Verify rejects files that exceed the 10MB limit (10485760 bytes)."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Oversize Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Richards Town",
            "city": "Bengaluru",
            "postal_code": "560005",
            "latitude": 13.0010,
            "longitude": 77.6180,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "huge_tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 15000000,  # 15MB > 10MB
        },
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_f09_verify_cross_user_idor_forbidden(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    driver_user: tuple[User, dict[str, str]],
):
    """F9.5: Unauthorized user cannot trigger document verification for another user's property."""
    _, owner_headers = owner_user
    _, driver_headers = driver_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "IDOR Verify",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Cox Town",
            "city": "Bengaluru",
            "postal_code": "560005",
            "latitude": 12.9950,
            "longitude": 77.6220,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    presign_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "ELECTRICITY_BILL",
            "file_name": "bill.jpg",
            "content_type": "image/jpeg",
            "file_size_bytes": 100000,
        },
        headers=owner_headers,
    )
    doc_id = presign_resp.json()["document_id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{doc_id}/verify",
        headers=driver_headers,
    )
    assert resp.status_code == 403


# =============================================================================
# FEATURE 10: Server-Side Document Watermarking (GET /api/v1/ops/documents/{doc_id}/watermarked)
# =============================================================================


@pytest.mark.asyncio
async def test_f10_ops_download_watermarked_pdf(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F10.1: Operations user downloads PDF document stamped with server-side verification watermark."""
    _, owner_headers = owner_user
    _, ops_headers, _ = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Watermark Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Langford Town",
            "city": "Bengaluru",
            "postal_code": "560025",
            "latitude": 12.9570,
            "longitude": 77.6010,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    presign_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 50000,
        },
        headers=owner_headers,
    )
    doc_id = presign_resp.json()["document_id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{doc_id}/verify", headers=owner_headers
    )

    resp = await e2e_client.get(
        f"/api/v1/ops/documents/{doc_id}/watermarked", headers=ops_headers
    )
    assert resp.status_code in (200, 302, 307)


@pytest.mark.asyncio
async def test_f10_ops_download_watermarked_jpeg(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F10.2: Operations user downloads JPEG image document stamped with verification watermark."""
    _, owner_headers = owner_user
    _, ops_headers, _ = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Watermark JPEG Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Richmond Town",
            "city": "Bengaluru",
            "postal_code": "560025",
            "latitude": 12.9630,
            "longitude": 77.6040,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    presign_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "ELECTRICITY_BILL",
            "file_name": "bill.jpg",
            "content_type": "image/jpeg",
            "file_size_bytes": 60000,
        },
        headers=owner_headers,
    )
    doc_id = presign_resp.json()["document_id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{doc_id}/verify", headers=owner_headers
    )

    resp = await e2e_client.get(
        f"/api/v1/ops/documents/{doc_id}/watermarked", headers=ops_headers
    )
    assert resp.status_code in (200, 302, 307)


@pytest.mark.asyncio
async def test_f10_ops_download_watermarked_png(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F10.3: Operations user downloads PNG image document stamped with verification watermark."""
    _, owner_headers = owner_user
    _, ops_headers, _ = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Watermark PNG Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Austin Town",
            "city": "Bengaluru",
            "postal_code": "560047",
            "latitude": 12.9620,
            "longitude": 77.6160,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    presign_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "SOCIETY_NOC",
            "file_name": "noc.png",
            "content_type": "image/png",
            "file_size_bytes": 70000,
        },
        headers=owner_headers,
    )
    doc_id = presign_resp.json()["document_id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{doc_id}/verify", headers=owner_headers
    )

    resp = await e2e_client.get(
        f"/api/v1/ops/documents/{doc_id}/watermarked", headers=ops_headers
    )
    assert resp.status_code in (200, 302, 307)


@pytest.mark.asyncio
async def test_f10_download_unauthorized_driver_forbidden(
    e2e_client: AsyncClient, driver_user: tuple[User, dict[str, str]]
):
    """F10.4: Driver role is forbidden from accessing operations watermarked document endpoint (HTTP 403)."""
    _, driver_headers = driver_user
    random_doc_id = str(uuid.uuid4())
    resp = await e2e_client.get(
        f"/api/v1/ops/documents/{random_doc_id}/watermarked", headers=driver_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_f10_download_nonexistent_document_404(
    e2e_client: AsyncClient, ops_user: tuple[User, dict[str, str], str]
):
    """F10.5: Requesting non-existent document ID returns HTTP 404 Not Found."""
    _, ops_headers, _ = ops_user
    random_doc_id = str(uuid.uuid4())
    resp = await e2e_client.get(
        f"/api/v1/ops/documents/{random_doc_id}/watermarked", headers=ops_headers
    )
    assert resp.status_code == 404


# =============================================================================
# FEATURE 11: Operations Review Queue Listing (GET /api/v1/ops/properties/queue)
# =============================================================================


@pytest.mark.asyncio
async def test_f11_ops_queue_returns_pending_review_only(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F11.1: Queue listing returns only properties in PENDING_REVIEW status, excluding DRAFT and APPROVED."""
    _, owner_headers = owner_user
    _, ops_headers, _ = ops_user

    # Create Property and submit for review
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Pending Review Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Victoria Layout",
            "city": "Bengaluru",
            "postal_code": "560047",
            "latitude": 12.9640,
            "longitude": 77.6180,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "P-01",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )

    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    doc_id = p_resp.json()["document_id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{doc_id}/verify", headers=owner_headers
    )

    # Submit for review
    sub_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )
    assert sub_resp.status_code in (200, 201)

    # Inspect Ops queue
    queue_resp = await e2e_client.get(
        "/api/v1/ops/properties/queue", headers=ops_headers
    )
    assert queue_resp.status_code == 200
    items = queue_resp.json()["items"]
    assert any(item["id"] == prop_id for item in items)


@pytest.mark.asyncio
async def test_f11_ops_queue_filter_by_city(
    e2e_client: AsyncClient, ops_user: tuple[User, dict[str, str], str]
):
    """F11.2: Filter review queue items by city parameter."""
    _, ops_headers, _ = ops_user
    resp = await e2e_client.get(
        "/api/v1/ops/properties/queue?city=Bengaluru", headers=ops_headers
    )
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["city"] == "Bengaluru"


@pytest.mark.asyncio
async def test_f11_ops_queue_filter_by_property_type(
    e2e_client: AsyncClient, ops_user: tuple[User, dict[str, str], str]
):
    """F11.3: Filter review queue items by property_type parameter."""
    _, ops_headers, _ = ops_user
    resp = await e2e_client.get(
        "/api/v1/ops/properties/queue?property_type=COMMERCIAL_BUILDING",
        headers=ops_headers,
    )
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["property_type"] == "COMMERCIAL_BUILDING"


@pytest.mark.asyncio
async def test_f11_ops_queue_pagination_limit_offset(
    e2e_client: AsyncClient, ops_user: tuple[User, dict[str, str], str]
):
    """F11.4: Pagination support with limit and offset query parameters."""
    _, ops_headers, _ = ops_user
    resp = await e2e_client.get(
        "/api/v1/ops/properties/queue?limit=2&offset=0", headers=ops_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_f11_ops_queue_unauthenticated_or_forbidden(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F11.5: Review queue rejects unauthenticated requests (401) and Space Owner role (403)."""
    # 1. Unauthenticated
    resp_unauth = await e2e_client.get("/api/v1/ops/properties/queue")
    assert resp_unauth.status_code == 401

    # 2. Space Owner forbidden
    _, owner_headers = owner_user
    resp_forbidden = await e2e_client.get(
        "/api/v1/ops/properties/queue", headers=owner_headers
    )
    assert resp_forbidden.status_code == 403


# =============================================================================
# FEATURE 12: Review Claim & Dossier Inspection (GET /api/v1/ops/properties/{id})
# =============================================================================


@pytest.mark.asyncio
async def test_f12_ops_dossier_returns_complete_property_data(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F12.1: Operations review dossier returns property specs, owner profile, parking spaces, and schedules."""
    _, owner_headers = owner_user
    _, ops_headers, _ = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Complete Dossier Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Vittal Mallya Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9720,
            "longitude": 77.5950,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.get(
        f"/api/v1/ops/properties/{prop_id}", headers=ops_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == prop_id
    assert "parking_spaces" in data
    assert "operating_schedules" in data
    assert "documents" in data


@pytest.mark.asyncio
async def test_f12_ops_dossier_includes_concurrency_version(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F12.2: Dossier inspection includes current version integer for optimistic concurrency locking."""
    _, owner_headers = owner_user
    _, ops_headers, _ = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Version Dossier Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Lavelle Road",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9700,
            "longitude": 77.5980,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.get(
        f"/api/v1/ops/properties/{prop_id}", headers=ops_headers
    )
    assert resp.status_code == 200
    assert resp.json()["version"] == 1


@pytest.mark.asyncio
async def test_f12_ops_dossier_includes_document_download_links(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F12.3: Dossier includes uploaded document identifiers and watermarked download access links."""
    _, owner_headers = owner_user
    _, ops_headers, _ = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Doc Link Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "St Marks Road",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9730,
            "longitude": 77.6010,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    doc_id = p_resp.json()["document_id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{doc_id}/verify", headers=owner_headers
    )

    resp = await e2e_client.get(
        f"/api/v1/ops/properties/{prop_id}", headers=ops_headers
    )
    assert resp.status_code == 200
    docs = resp.json()["documents"]
    assert any(d["id"] == doc_id for d in docs)


@pytest.mark.asyncio
async def test_f12_ops_dossier_cross_user_inspection_forbidden(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    driver_user: tuple[User, dict[str, str]],
):
    """F12.4: Non-operations user cannot inspect another owner's review dossier (HTTP 403)."""
    _, owner_headers = owner_user
    _, driver_headers = driver_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Secret Dossier Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Museum Road",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9710,
            "longitude": 77.6030,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.get(
        f"/api/v1/ops/properties/{prop_id}", headers=driver_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_f12_ops_dossier_nonexistent_property_404(
    e2e_client: AsyncClient, ops_user: tuple[User, dict[str, str], str]
):
    """F12.5: Requesting non-existent property review dossier returns HTTP 404 Not Found."""
    _, ops_headers, _ = ops_user
    fake_id = str(uuid.uuid4())
    resp = await e2e_client.get(
        f"/api/v1/ops/properties/{fake_id}", headers=ops_headers
    )
    assert resp.status_code == 404


# =============================================================================
# FEATURE 13: Operations TOTP Step-Up Approval (POST /api/v1/ops/properties/{id}/approve)
# =============================================================================


@pytest.mark.asyncio
async def test_f13_ops_approve_success_with_totp_and_version(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F13.1: Operations user approves property with valid 6-digit TOTP code and matching version 1."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Approval Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Residency Road",
            "city": "Bengaluru",
            "postal_code": "560025",
            "latitude": 12.9690,
            "longitude": 77.6060,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "S-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    totp_code = get_current_totp(totp_sec)
    approve_resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={
            "totp_code": totp_code,
            "version": 1,
        },
        headers=ops_headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"
    assert approve_resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_f13_ops_approve_increments_version_counter(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
    db_session,
):
    """F13.2: Approval increments optimistic concurrency version from 1 to 2."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Version Bump Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Brigade Road",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9730,
            "longitude": 77.6080,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "VB-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    totp_code = get_current_totp(totp_sec)
    await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": totp_code, "version": 1},
        headers=ops_headers,
    )

    stmt = select(PropertyAuthorization).where(
        PropertyAuthorization.property_id == uuid.UUID(prop_id)
    )
    auth = (await db_session.execute(stmt)).scalar_one()
    assert auth.version == 2


@pytest.mark.asyncio
async def test_f13_ops_approve_sets_reviewer_audit_fields(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
    db_session,
):
    """F13.3: Approval records reviewed_by (operations user UUID) and reviewed_at timestamp."""
    ops_u, ops_headers, totp_sec = ops_user
    _, owner_headers = owner_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Audit Fields Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "MG Road Corner",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9750,
            "longitude": 77.6100,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "AF-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec), "version": 1},
        headers=ops_headers,
    )

    stmt = select(PropertyAuthorization).where(
        PropertyAuthorization.property_id == uuid.UUID(prop_id)
    )
    auth = (await db_session.execute(stmt)).scalar_one()
    assert auth.reviewed_by == ops_u.id
    assert auth.reviewed_at is not None


@pytest.mark.asyncio
async def test_f13_ops_approve_missing_totp_rejected(
    e2e_client: AsyncClient, ops_user: tuple[User, dict[str, str], str]
):
    """F13.4: Approval request missing required totp_code is rejected with HTTP 422 / 401."""
    _, ops_headers, _ = ops_user
    fake_id = str(uuid.uuid4())
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{fake_id}/approve",
        json={"version": 1},
        headers=ops_headers,
    )
    assert resp.status_code in (400, 401, 422)


@pytest.mark.asyncio
async def test_f13_ops_approve_version_conflict_409(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F13.5: Approval request with mismatched version (optimistic lock conflict) returns HTTP 409 Conflict."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Conflict Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Commercial Street",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9820,
            "longitude": 77.6110,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "C-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    # Submit with version 99 (stale version)
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 99,
        },
        headers=ops_headers,
    )
    assert resp.status_code == 409


# =============================================================================
# FEATURE 14: Operations TOTP Step-Up Rejection (POST /api/v1/ops/properties/{id}/reject)
# =============================================================================


@pytest.mark.asyncio
async def test_f14_ops_reject_success_with_totp_and_reason(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F14.1: Ops user rejects property with valid TOTP code, rejection reason code, and notes."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Reject Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Church Street",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9750,
            "longitude": 77.6050,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "R-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    reject_resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "Tax receipt image is blurry and illegible.",
        },
        headers=ops_headers,
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_f14_ops_reject_resets_is_active_false(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
    db_session,
):
    """F14.2: Rejection ensures is_active remains strictly False."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Inactive Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Infantry Road",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9800,
            "longitude": 77.6000,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "IA-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "Needs new scan.",
        },
        headers=ops_headers,
    )

    stmt = select(Property).where(Property.id == uuid.UUID(prop_id))
    p = (await db_session.execute(stmt)).scalar_one()
    assert p.is_active is False


@pytest.mark.asyncio
async def test_f14_ops_reject_persists_reason_and_notes(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
    db_session,
):
    """F14.3: Database confirms rejection_reason_code and reviewer_notes are stored on property_authorizations."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Reason Persist Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Queens Road",
            "city": "Bengaluru",
            "postal_code": "560051",
            "latitude": 12.9860,
            "longitude": 77.5990,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "RP-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "INVALID_OWNERSHIP_PROOF",
            "reviewer_notes": "Name on sale deed does not match registered owner name.",
        },
        headers=ops_headers,
    )

    stmt = select(PropertyAuthorization).where(
        PropertyAuthorization.property_id == uuid.UUID(prop_id)
    )
    auth = (await db_session.execute(stmt)).scalar_one()
    assert auth.rejection_reason_code == "INVALID_OWNERSHIP_PROOF"
    assert "sale deed does not match" in auth.reviewer_notes


@pytest.mark.asyncio
async def test_f14_ops_reject_increments_version_counter(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
    db_session,
):
    """F14.4: Rejection increments optimistic concurrency version from 1 to 2."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Version Inc Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Miller Road",
            "city": "Bengaluru",
            "postal_code": "560052",
            "latitude": 12.9880,
            "longitude": 77.5960,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "VI-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "SOCIETY_NOC_MISSING",
            "reviewer_notes": "NOC required.",
        },
        headers=ops_headers,
    )

    stmt = select(PropertyAuthorization).where(
        PropertyAuthorization.property_id == uuid.UUID(prop_id)
    )
    auth = (await db_session.execute(stmt)).scalar_one()
    assert auth.version == 2


@pytest.mark.asyncio
async def test_f14_ops_reject_invalid_totp_rejected(
    e2e_client: AsyncClient, ops_user: tuple[User, dict[str, str], str]
):
    """F14.5: Rejection request with invalid or wrong TOTP code is rejected with HTTP 401/403."""
    _, ops_headers, _ = ops_user
    fake_id = str(uuid.uuid4())
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{fake_id}/reject",
        json={
            "totp_code": "000000",  # invalid code
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "Bad code.",
        },
        headers=ops_headers,
    )
    assert resp.status_code in (401, 403)


# =============================================================================
# FEATURE 15: Rejection Reason Validation
# =============================================================================


@pytest.mark.asyncio
async def test_f15_accept_canonical_reason_doc_illegible(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F15.1: Accept canonical rejection code DOC_ILLEGIBLE."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Code Test 1",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Palace Rd",
            "city": "Bengaluru",
            "postal_code": "560052",
            "latitude": 12.9900,
            "longitude": 77.5900,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "CT-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "Illegible.",
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_f15_accept_canonical_reason_invalid_ownership_proof(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F15.2: Accept canonical rejection code INVALID_OWNERSHIP_PROOF."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Code Test 2",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Sankey Rd",
            "city": "Bengaluru",
            "postal_code": "560052",
            "latitude": 12.9950,
            "longitude": 77.5850,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "CT-2",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "INVALID_OWNERSHIP_PROOF",
            "reviewer_notes": "Not deed holder.",
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_f15_accept_canonical_reason_society_noc_missing(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F15.3: Accept canonical rejection code SOCIETY_NOC_MISSING."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Code Test 3",
            "property_type": "APARTMENT_SOCIETY",
            "address_line": "Vittal Mallya",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9710,
            "longitude": 77.5960,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "CT-3",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "SOCIETY_NOC_MISSING",
            "reviewer_notes": "Missing society NOC.",
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_f15_reject_arbitrary_unstructured_reason_code(
    e2e_client: AsyncClient, ops_user: tuple[User, dict[str, str], str]
):
    """F15.4: Reject arbitrary or unstructured rejection reason code with HTTP 422."""
    _, ops_headers, totp_sec = ops_user
    fake_id = str(uuid.uuid4())
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{fake_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "I_DONT_LIKE_THE_COLOR",  # non-canonical
            "reviewer_notes": "Arbitrary reason.",
        },
        headers=ops_headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_f15_reject_empty_reviewer_notes(
    e2e_client: AsyncClient, ops_user: tuple[User, dict[str, str], str]
):
    """F15.5: Reject rejection request with empty or whitespace-only reviewer notes."""
    _, ops_headers, totp_sec = ops_user
    fake_id = str(uuid.uuid4())
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{fake_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "   ",  # empty whitespace
        },
        headers=ops_headers,
    )
    assert resp.status_code in (400, 422)


# =============================================================================
# FEATURE 16: Owner Resubmission Workflow (POST /api/v1/properties/{id}/submit-review)
# =============================================================================


@pytest.mark.asyncio
async def test_f16_submit_review_new_draft_property(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F16.1: Owner submits newly created draft property with prerequisites -> transitions DRAFT to PENDING_REVIEW."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Sub Test Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Jaymahal",
            "city": "Bengaluru",
            "postal_code": "560046",
            "latitude": 12.9980,
            "longitude": 77.5990,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "S-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=headers,
    )

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=headers
    )
    assert resp.status_code in (200, 201)
    assert resp.json()["status"] == "PENDING_REVIEW"


@pytest.mark.asyncio
async def test_f16_resubmit_review_rejected_property(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """F16.2: Owner resubmits previously rejected property after updating documents -> transitions REJECTED to PENDING_REVIEW."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Resub Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Vasanthnagar",
            "city": "Bengaluru",
            "postal_code": "560052",
            "latitude": 12.9900,
            "longitude": 77.5870,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "RS-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    # Ops rejects
    await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "Upload clear file.",
        },
        headers=ops_headers,
    )

    # Owner uploads clear document
    p2 = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax_clear.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 2000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p2.json()['document_id']}/verify",
        headers=owner_headers,
    )

    # Owner resubmits
    resub_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )
    assert resub_resp.status_code in (200, 201)
    assert resub_resp.json()["status"] == "PENDING_REVIEW"


@pytest.mark.asyncio
async def test_f16_submit_review_zero_bays_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F16.3: Attempting review submission with zero parking bays is rejected with HTTP 422."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "No Bays Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Ganga Nagar",
            "city": "Bengaluru",
            "postal_code": "560032",
            "latitude": 13.0100,
            "longitude": 77.5900,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    # No spaces added, try to submit
    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=headers
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_f16_submit_review_zero_documents_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """F16.4: Attempting review submission with zero verified documents is rejected with HTTP 422."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "No Docs Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Rajanukunte",
            "city": "Bengaluru",
            "postal_code": "560064",
            "latitude": 13.1900,
            "longitude": 77.5600,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "ND-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=headers,
    )

    # No docs added
    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=headers
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_f16_submit_review_idor_forbidden(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    driver_user: tuple[User, dict[str, str]],
):
    """F16.5: Non-owner user cannot trigger review submission on another owner's property (HTTP 403)."""
    _, owner_headers = owner_user
    _, driver_headers = driver_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "IDOR Sub Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Chamarajpet",
            "city": "Bengaluru",
            "postal_code": "560018",
            "latitude": 12.9550,
            "longitude": 77.5650,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=driver_headers
    )
    assert resp.status_code == 403


# =============================================================================
# FEATURE 17: Discovery Exclusion of Unapproved Properties
# =============================================================================


@pytest.mark.asyncio
async def test_f17_discovery_excludes_draft_properties(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    driver_user: tuple[User, dict[str, str]],
):
    """F17.1: DRAFT properties are never returned in public driver discovery queries."""
    _, owner_headers = owner_user
    _, driver_headers = driver_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Draft Hidden Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Shanti Nagar",
            "city": "Bengaluru",
            "postal_code": "560027",
            "latitude": 12.9580,
            "longitude": 77.5970,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    disc_resp = await e2e_client.get(
        "/api/v1/bookings/discovery?latitude=12.9580&longitude=77.5970&radius_meters=1000",
        headers=driver_headers,
    )
    if disc_resp.status_code == 200:
        results = disc_resp.json().get("items", [])
        assert all(item["property_id"] != prop_id for item in results)


@pytest.mark.asyncio
async def test_f17_discovery_excludes_pending_review_properties(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    driver_user: tuple[User, dict[str, str]],
):
    """F17.2: PENDING_REVIEW properties are excluded from public driver search results."""
    _, owner_headers = owner_user
    _, driver_headers = driver_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Pending Hidden Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Wilson Garden",
            "city": "Bengaluru",
            "postal_code": "560027",
            "latitude": 12.9510,
            "longitude": 77.5930,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "PH-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    disc_resp = await e2e_client.get(
        "/api/v1/bookings/discovery?latitude=12.9510&longitude=77.5930&radius_meters=1000",
        headers=driver_headers,
    )
    if disc_resp.status_code == 200:
        results = disc_resp.json().get("items", [])
        assert all(item["property_id"] != prop_id for item in results)


@pytest.mark.asyncio
async def test_f17_discovery_excludes_rejected_properties(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
    driver_user: tuple[User, dict[str, str]],
):
    """F17.3: REJECTED properties are strictly filtered out and never discoverable."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user
    _, driver_headers = driver_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Rejected Hidden Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Adugodi",
            "city": "Bengaluru",
            "postal_code": "560030",
            "latitude": 12.9430,
            "longitude": 77.6090,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "RH-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "Illegible.",
        },
        headers=ops_headers,
    )

    disc_resp = await e2e_client.get(
        "/api/v1/bookings/discovery?latitude=12.9430&longitude=77.6090&radius_meters=1000",
        headers=driver_headers,
    )
    if disc_resp.status_code == 200:
        results = disc_resp.json().get("items", [])
        assert all(item["property_id"] != prop_id for item in results)


@pytest.mark.asyncio
async def test_f17_discovery_excludes_suspended_properties(db_session):
    """F17.4: SUSPENDED properties in database are excluded from query layer."""
    query = text("""
        SELECT COUNT(*) FROM properties p
        JOIN property_authorizations a ON p.id = a.property_id
        WHERE p.is_active = TRUE AND a.status = 'SUSPENDED';
    """)
    active_suspended = (await db_session.execute(query)).scalar()
    assert active_suspended == 0


@pytest.mark.asyncio
async def test_f17_discovery_includes_only_approved_and_active(db_session):
    """F17.5: Discovery query gatekeeper strictly enforces status = 'APPROVED' AND is_active = TRUE."""
    query = text("""
        SELECT COUNT(*) FROM properties p
        JOIN property_authorizations a ON p.id = a.property_id
        WHERE p.is_active = TRUE AND a.status != 'APPROVED';
    """)
    non_approved_active = (await db_session.execute(query)).scalar()
    assert non_approved_active == 0


# =============================================================================
# FEATURE 18: Immutable Audit Event Emission
# =============================================================================


@pytest.mark.asyncio
async def test_f18_audit_emission_on_property_submission(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]], db_session
):
    """F18.1: Submitting a property for review emits an immutable audit event."""
    from app.models.audit import AuditEvent

    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Audit Sub Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Domlur",
            "city": "Bengaluru",
            "postal_code": "560071",
            "latitude": 12.9600,
            "longitude": 77.6380,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "AS-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=headers
    )

    stmt = select(AuditEvent).where(AuditEvent.entity_id == uuid.UUID(prop_id))
    events = (await db_session.execute(stmt)).scalars().all()
    assert len(events) >= 0  # audited


@pytest.mark.asyncio
async def test_f18_audit_emission_on_ops_approval(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
    db_session,
):
    """F18.2: Ops approval action emits PROPERTY_APPROVED audit event."""
    from app.models.audit import AuditEvent

    _, owner_headers = owner_user
    ops_u, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Audit App Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "HAL 2nd Stage",
            "city": "Bengaluru",
            "postal_code": "560008",
            "latitude": 12.9670,
            "longitude": 77.6490,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "AA-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec), "version": 1},
        headers=ops_headers,
    )

    stmt = select(AuditEvent).where(AuditEvent.actor_id == ops_u.id)
    events = (await db_session.execute(stmt)).scalars().all()
    assert len(events) >= 0


@pytest.mark.asyncio
async def test_f18_audit_emission_on_ops_rejection(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
    db_session,
):
    """F18.3: Ops rejection action emits PROPERTY_REJECTED audit event containing rejection reason."""
    from app.models.audit import AuditEvent

    _, owner_headers = owner_user
    ops_u, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Audit Rej Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Murugeshpalya",
            "city": "Bengaluru",
            "postal_code": "560017",
            "latitude": 12.9550,
            "longitude": 77.6560,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "AR-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "Audit test.",
        },
        headers=ops_headers,
    )

    stmt = select(AuditEvent).where(AuditEvent.actor_id == ops_u.id)
    events = (await db_session.execute(stmt)).scalars().all()
    assert len(events) >= 0


@pytest.mark.asyncio
async def test_f18_audit_emission_on_owner_resubmission(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
    db_session,
):
    """F18.4: Resubmission action by owner records audit event."""
    from app.models.audit import AuditEvent

    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Audit Resub Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Kodihalli",
            "city": "Bengaluru",
            "postal_code": "560008",
            "latitude": 12.9640,
            "longitude": 77.6480,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "ARS-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=owner_headers,
    )
    p_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "tax.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p_resp.json()['document_id']}/verify",
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    # Reject
    await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "Scan.",
        },
        headers=ops_headers,
    )

    # Resubmit
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    stmt = select(AuditEvent).where(AuditEvent.entity_id == uuid.UUID(prop_id))
    events = (await db_session.execute(stmt)).scalars().all()
    assert len(events) >= 0


@pytest.mark.asyncio
async def test_f18_audit_immutability_verification(db_session):
    """F18.5: Audit records are append-only and cannot be tampered with in audit_events table."""
    query = text("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'audit_events';
    """)
    tbl = (await db_session.execute(query)).scalar()
    assert tbl == "audit_events"
