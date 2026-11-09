"""Unit and integration API test suite for Parking Bay Inventory & Vehicle Compatibility Engine."""

import uuid

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
from app.models.properties import Property
from app.models.users import User, UserRole
from app.services.property_service import PropertyService
from httpx import ASGITransport, AsyncClient


async def _create_owner(db_session, suffix="bay") -> tuple[User, dict[str, str]]:
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


async def _create_property_for_owner(db_session, owner_id: uuid.UUID) -> Property:
    """Helper to persist a property in the database."""
    prop = Property(
        owner_id=owner_id,
        title="Bay Inventory Plaza",
        property_type="COMMERCIAL_BUILDING",
        address_line="100 Feet Road, Indiranagar",
        city="Bengaluru",
        postal_code="560038",
        location=PropertyService.make_point_wkt(12.9784, 77.6408),
        is_active=False,
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)
    return prop


@pytest.mark.asyncio
async def test_create_standard_covered_bay_success(db_session):
    """Verify owner creates a standard covered car bay with valid dimensions and tariff."""
    owner, headers = await _create_owner(db_session, "std_bay")
    prop = await _create_property_for_owner(db_session, owner.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "space_label": "BAY-C01",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "has_ev_charging": False,
            "base_hourly_rate_paise": 6000,
        }
        resp = await client.post(f"/api/v1/properties/{prop.id}/spaces", json=payload, headers=headers)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "id" in data
        assert data["space_label"] == "BAY-C01"
        assert data["vehicle_category"] == "SEDAN"
        assert float(data["length_meters"]) == 4.80
        assert float(data["width_meters"]) == 2.40
        assert float(data["height_clearance_meters"]) == 2.10
        assert data["has_ev_charging"] is False
        assert data["base_hourly_rate_paise"] == 6000
        assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_ev_charging_bay(db_session):
    """Verify creating a dedicated EV bay persists has_ev_charging=True."""
    owner, headers = await _create_owner(db_session, "ev_bay")
    prop = await _create_property_for_owner(db_session, owner.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "space_label": "EV-FAST-01",
            "space_type": "COVERED",
            "vehicle_category": "EV_FOUR_WHEELER",
            "length_meters": 5.00,
            "width_meters": 2.50,
            "height_clearance_meters": 2.20,
            "has_ev_charging": True,
            "base_hourly_rate_paise": 8500,
        }
        resp = await client.post(f"/api/v1/properties/{prop.id}/spaces", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["has_ev_charging"] is True
        assert data["vehicle_category"] == "EV_FOUR_WHEELER"


@pytest.mark.asyncio
async def test_create_duplicate_space_label_on_same_property_rejected(db_session):
    """Verify duplicate space label on the same property is rejected with 409 Conflict."""
    owner, headers = await _create_owner(db_session, "dup_bay")
    prop = await _create_property_for_owner(db_session, owner.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "space_label": "BAY-UNIQUE",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        }
        resp1 = await client.post(f"/api/v1/properties/{prop.id}/spaces", json=payload, headers=headers)
        assert resp1.status_code == 201

        resp2 = await client.post(f"/api/v1/properties/{prop.id}/spaces", json=payload, headers=headers)
        assert resp2.status_code == 409
        assert resp2.json()["code"] == "DUPLICATE_SPACE_LABEL"


@pytest.mark.asyncio
async def test_create_space_cross_owner_idor_forbidden(db_session):
    """Verify an owner cannot add spaces to another owner's property (HTTP 403 Forbidden)."""
    owner1, _ = await _create_owner(db_session, "owner1_bay")
    _owner2, headers2 = await _create_owner(db_session, "owner2_bay")
    prop1 = await _create_property_for_owner(db_session, owner1.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "space_label": "ATTACK-BAY",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        }
        resp = await client.post(f"/api/v1/properties/{prop1.id}/spaces", json=payload, headers=headers2)
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_space_invalid_dimensions_or_tariff_rejected(db_session):
    """Verify non-positive dimensions and non-positive hourly rate are rejected with 422."""
    owner, headers = await _create_owner(db_session, "invalid_bay")
    prop = await _create_property_for_owner(db_session, owner.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Zero length
        resp1 = await client.post(
            f"/api/v1/properties/{prop.id}/spaces",
            json={
                "space_label": "BAY-BAD-1",
                "space_type": "COVERED",
                "vehicle_category": "SEDAN",
                "length_meters": 0.0,
                "width_meters": 2.40,
                "height_clearance_meters": 2.10,
                "base_hourly_rate_paise": 5000,
            },
            headers=headers,
        )
        assert resp1.status_code == 422

        # Negative tariff
        resp2 = await client.post(
            f"/api/v1/properties/{prop.id}/spaces",
            json={
                "space_label": "BAY-BAD-2",
                "space_type": "COVERED",
                "vehicle_category": "SEDAN",
                "length_meters": 4.80,
                "width_meters": 2.40,
                "height_clearance_meters": 2.10,
                "base_hourly_rate_paise": -500,
            },
            headers=headers,
        )
        assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_get_list_and_update_space(db_session):
    """Verify listing spaces on a property, retrieving a space by ID, and mutating dimensions/tariff."""
    owner, headers = await _create_owner(db_session, "crud_bay")
    prop = await _create_property_for_owner(db_session, owner.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create two bays
        p1 = await client.post(
            f"/api/v1/properties/{prop.id}/spaces",
            json={
                "space_label": "B-01",
                "space_type": "COVERED",
                "vehicle_category": "SEDAN",
                "length_meters": 4.80,
                "width_meters": 2.40,
                "height_clearance_meters": 2.10,
                "base_hourly_rate_paise": 5000,
            },
            headers=headers,
        )
        space1_id = p1.json()["id"]

        await client.post(
            f"/api/v1/properties/{prop.id}/spaces",
            json={
                "space_label": "B-02",
                "space_type": "OPEN",
                "vehicle_category": "TWO_WHEELER",
                "length_meters": 2.20,
                "width_meters": 1.00,
                "height_clearance_meters": 2.00,
                "base_hourly_rate_paise": 2000,
            },
            headers=headers,
        )

        # 2. List spaces on property
        list_resp = await client.get(f"/api/v1/properties/{prop.id}/spaces", headers=headers)
        assert list_resp.status_code == 200
        labels = [s["space_label"] for s in list_resp.json()]
        assert "B-01" in labels
        assert "B-02" in labels

        # 3. Get single space by ID
        get_resp = await client.get(f"/api/v1/spaces/{space1_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["space_label"] == "B-01"

        # 4. Update space 1 (tariff and EV charging toggle)
        upd_resp = await client.put(
            f"/api/v1/spaces/{space1_id}",
            json={
                "base_hourly_rate_paise": 7500,
                "has_ev_charging": True,
            },
            headers=headers,
        )
        assert upd_resp.status_code == 200
        assert upd_resp.json()["base_hourly_rate_paise"] == 7500
        assert upd_resp.json()["has_ev_charging"] is True


@pytest.mark.asyncio
async def test_vehicle_compatibility_3d_margins(db_session):
    """Verify 3D physical clearance compatibility evaluation (+300mm length, +400mm width, +100mm height)."""
    owner, headers = await _create_owner(db_session, "compat_3d")
    prop = await _create_property_for_owner(db_session, owner.id)

    # Standard bay: 4.80m length (4800mm), 2.40m width (2400mm), 2.10m height (2100mm)
    space = ParkingSpace(
        property_id=prop.id,
        space_label="COMPAT-BAY",
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
    await db_session.refresh(space)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Sedan: 4400mm length, 1800mm width, 1500mm height
        # Clearances: 4800-4400=400mm (>=300), 2400-1800=600mm (>=400), 2100-1500=600mm (>=100) -> Compatible!
        compat_resp = await client.post(
            f"/api/v1/spaces/{space.id}/compatibility",
            json={
                "vehicle_category": "SEDAN",
                "vehicle_length_mm": 4400,
                "vehicle_width_mm": 1800,
                "vehicle_height_mm": 1500,
            },
            headers=headers,
        )
        assert compat_resp.status_code == 200
        res = compat_resp.json()
        assert res["is_compatible"] is True
        assert res["method"] == "3d_clearance"
        assert res["length_clearance_mm"] == 400
        assert res["width_clearance_mm"] == 600

        # Oversized SUV: 4900mm length (> 4800mm space length) -> Incompatible!
        incompat_resp = await client.post(
            f"/api/v1/spaces/{space.id}/compatibility",
            json={
                "vehicle_category": "SUV",
                "vehicle_length_mm": 4900,
                "vehicle_width_mm": 2100,
                "vehicle_height_mm": 1900,
            },
            headers=headers,
        )
        assert incompat_resp.status_code == 200
        incompat_res = incompat_resp.json()
        assert incompat_res["is_compatible"] is False
        assert any("length clearance" in r.lower() for r in incompat_res["rejection_reasons"])


@pytest.mark.asyncio
async def test_vehicle_compatibility_ev_charging_requirement(db_session):
    """Verify EV vehicles require dedicated EV charging bays if requested or if EV flag set."""
    owner, headers = await _create_owner(db_session, "compat_ev")
    prop = await _create_property_for_owner(db_session, owner.id)

    # Bay WITHOUT EV charging
    space_no_ev = ParkingSpace(
        property_id=prop.id,
        space_label="NON-EV-BAY",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        length_meters=5.00,
        width_meters=2.50,
        height_clearance_meters=2.20,
        has_ev_charging=False,
        base_hourly_rate_paise=5000,
    )
    # Bay WITH EV charging
    space_with_ev = ParkingSpace(
        property_id=prop.id,
        space_label="EV-BAY",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        length_meters=5.00,
        width_meters=2.50,
        height_clearance_meters=2.20,
        has_ev_charging=True,
        base_hourly_rate_paise=7000,
    )
    db_session.add_all([space_no_ev, space_with_ev])
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # EV vehicle on Non-EV bay -> Incompatible
        resp1 = await client.post(
            f"/api/v1/spaces/{space_no_ev.id}/compatibility",
            json={
                "vehicle_category": "SEDAN",
                "vehicle_length_mm": 4500,
                "vehicle_width_mm": 1800,
                "vehicle_height_mm": 1500,
                "is_ev": True,
            },
            headers=headers,
        )
        assert resp1.status_code == 200
        assert resp1.json()["is_compatible"] is False
        assert any("charging" in r.lower() for r in resp1.json()["rejection_reasons"])

        # EV vehicle on EV bay -> Compatible
        resp2 = await client.post(
            f"/api/v1/spaces/{space_with_ev.id}/compatibility",
            json={
                "vehicle_category": "SEDAN",
                "vehicle_length_mm": 4500,
                "vehicle_width_mm": 1800,
                "vehicle_height_mm": 1500,
                "is_ev": True,
            },
            headers=headers,
        )
        assert resp2.status_code == 200
        assert resp2.json()["is_compatible"] is True


@pytest.mark.asyncio
async def test_vehicle_compatibility_stored_function_fallback(db_session):
    """Verify category-level check invokes PostgreSQL fn_check_vehicle_bay_compatibility."""
    owner, headers = await _create_owner(db_session, "compat_fn")
    prop = await _create_property_for_owner(db_session, owner.id)

    space = ParkingSpace(
        property_id=prop.id,
        space_label="FN-BAY",
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Category check without mm dimensions -> calls stored function
        resp = await client.post(
            f"/api/v1/spaces/{space.id}/compatibility",
            json={
                "vehicle_category": "SEDAN",
                "driver_requires_ev": False,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["method"] == "stored_function"
        assert data["is_compatible"] is True
