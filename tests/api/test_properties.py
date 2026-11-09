"""Unit and integration API test suite for Property Management and Location Services."""

import uuid

import pytest
from app.core.security import create_access_token
from app.main import app
from app.models.documents import PropertyDocument
from app.models.enums import (
    AccountStatus,
    AuthorizationStatusEnum,
    DocumentTypeEnum,
    PropertyTypeEnum,
    UserRoleEnum,
    VehicleCategoryEnum,
)
from app.models.parking import ParkingSpace
from app.models.properties import Property, PropertyAuthorization
from app.models.users import User, UserRole
from app.services.property_service import PropertyService
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text


async def _create_owner(db_session, suffix="prop") -> tuple[User, dict[str, str]]:
    """Helper to provision an active OWNER user with valid Bearer token."""
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
    """Helper to provision an active DRIVER user with valid Bearer token."""
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


@pytest.mark.asyncio
async def test_create_property_success_and_postgis_persistence(db_session):
    """Verify space owner creates property with PostGIS WGS 84 Point geometry, DRAFT status, and version=1."""
    _owner, headers = await _create_owner(db_session, "create_ok")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "title": "Green Glen Residency",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "123 Outer Ring Road, Bellandur",
            "city": "Bengaluru",
            "postal_code": "560103",
            "latitude": 12.9352,
            "longitude": 77.6772,
            "max_advance_days": 14,
            "max_booking_hours": 48,
        }
        resp = await client.post("/api/v1/properties", json=payload, headers=headers)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "id" in data
        assert data["title"] == payload["title"]
        assert data["property_type"] == "RESIDENTIAL_DRIVEWAY"
        assert data["city"] == "Bengaluru"
        assert data["latitude"] == pytest.approx(12.9352, abs=1e-4)
        assert data["longitude"] == pytest.approx(77.6772, abs=1e-4)
        assert data["is_active"] is False

        # Verify linked authorization record
        prop_id = uuid.UUID(data["id"])
        stmt = select(PropertyAuthorization).where(PropertyAuthorization.property_id == prop_id)
        auth = (await db_session.execute(stmt)).scalar_one()
        assert auth.status == AuthorizationStatusEnum.DRAFT
        assert auth.version == 1

        # Verify database PostGIS spatial geometry
        raw_query = text("SELECT ST_AsText(location), ST_SRID(location) FROM properties WHERE id = :id")
        row = (await db_session.execute(raw_query, {"id": prop_id})).fetchone()
        assert row is not None
        assert row[0] == "POINT(77.6772 12.9352)"
        assert row[1] == 4326


@pytest.mark.asyncio
async def test_create_property_invalid_coordinates_rejected(db_session):
    """Verify latitude [-90,90] and longitude [-180,180] strict boundaries are enforced."""
    _, headers = await _create_owner(db_session, "invalid_coords")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid latitude (> 90)
        resp1 = await client.post(
            "/api/v1/properties",
            json={
                "title": "Invalid Lat Prop",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "Road 1",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 95.0,
                "longitude": 77.0,
            },
            headers=headers,
        )
        assert resp1.status_code == 422

        # Invalid longitude (< -180)
        resp2 = await client.post(
            "/api/v1/properties",
            json={
                "title": "Invalid Lon Prop",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "Road 2",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.0,
                "longitude": -185.0,
            },
            headers=headers,
        )
        assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_create_property_invalid_postal_code_rejected(db_session):
    """Verify postal_code pattern strictly enforces 6-digit Indian PIN code."""
    _, headers = await _create_owner(db_session, "invalid_pin")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 5 digits
        resp = await client.post(
            "/api/v1/properties",
            json={
                "title": "Short PIN",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "Road 1",
                "city": "Bengaluru",
                "postal_code": "56001",
                "latitude": 12.0,
                "longitude": 77.0,
            },
            headers=headers,
        )
        assert resp.status_code == 422

        # Letters in PIN
        resp2 = await client.post(
            "/api/v1/properties",
            json={
                "title": "Alpha PIN",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "Road 1",
                "city": "Bengaluru",
                "postal_code": "56000A",
                "latitude": 12.0,
                "longitude": 77.0,
            },
            headers=headers,
        )
        assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_create_property_unauthorized_and_unauthenticated_rejected(db_session):
    """Verify unauthenticated requests return 401 and DRIVER role returns 403."""
    _driver, driver_headers = await _create_driver(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "title": "Unauth Test",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "MG Road",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        }
        # 1. Unauthenticated (no token) -> 401
        resp_unauth = await client.post("/api/v1/properties", json=payload)
        assert resp_unauth.status_code == 401

        # 2. Driver role -> 403
        resp_forbidden = await client.post("/api/v1/properties", json=payload, headers=driver_headers)
        assert resp_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_list_owner_properties_isolation(db_session):
    """Verify owner listing returns only properties belonging to the authenticated owner."""
    _owner1, headers1 = await _create_owner(db_session, "list1")
    _owner2, headers2 = await _create_owner(db_session, "list2")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create property for owner 1
        p1 = await client.post(
            "/api/v1/properties",
            json={
                "title": "Owner 1 Property",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "Addr 1",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=headers1,
        )
        assert p1.status_code == 201
        p1_id = p1.json()["id"]

        # Owner 1 lists properties -> contains p1_id
        res1 = await client.get("/api/v1/properties", headers=headers1)
        assert res1.status_code == 200
        ids1 = [p["id"] for p in res1.json()]
        assert p1_id in ids1

        # Owner 2 lists properties -> does NOT contain p1_id
        res2 = await client.get("/api/v1/properties", headers=headers2)
        assert res2.status_code == 200
        ids2 = [p["id"] for p in res2.json()]
        assert p1_id not in ids2


@pytest.mark.asyncio
async def test_get_and_update_property(db_session):
    """Verify retrieving property details and updating metadata and coordinates."""
    _owner, headers = await _create_owner(db_session, "update_prop")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/properties",
            json={
                "title": "Initial Title",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "Initial Address",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=headers,
        )
        prop_id = create_resp.json()["id"]

        # Update title and coordinates
        update_resp = await client.put(
            f"/api/v1/properties/{prop_id}",
            json={
                "title": "Updated Title",
                "latitude": 12.9800,
                "longitude": 77.6000,
            },
            headers=headers,
        )
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["title"] == "Updated Title"
        assert data["latitude"] == pytest.approx(12.9800, abs=1e-4)
        assert data["longitude"] == pytest.approx(77.6000, abs=1e-4)

        # Get details
        get_resp = await client.get(f"/api/v1/properties/{prop_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_update_property_cross_owner_idor_forbidden(db_session):
    """Verify that an owner cannot update another owner's property (IDOR protection)."""
    _owner1, headers1 = await _create_owner(db_session, "idor_prop1")
    _owner2, headers2 = await _create_owner(db_session, "idor_prop2")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/properties",
            json={
                "title": "Protected Property",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "Protected Road",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=headers1,
        )
        prop_id = create_resp.json()["id"]

        # Owner 2 attempts update -> 403
        bad_update = await client.put(
            f"/api/v1/properties/{prop_id}",
            json={"title": "Hacked Title"},
            headers=headers2,
        )
        assert bad_update.status_code == 403


@pytest.mark.asyncio
async def test_submit_property_for_review_workflow(db_session):
    """Verify review submission transitions DRAFT -> PENDING_REVIEW after verifying bays and documents."""
    _owner, headers = await _create_owner(db_session, "submit_ok")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create property
        create_resp = await client.post(
            "/api/v1/properties",
            json={
                "title": "Submission Ready Prop",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "Ready Lane",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=headers,
        )
        prop_id = uuid.UUID(create_resp.json()["id"])

        # 2. Add parking bay
        space = ParkingSpace(
            property_id=prop_id,
            space_label="BAY-1",
            vehicle_category=VehicleCategoryEnum.SEDAN,
            length_meters=4.80,
            width_meters=2.40,
            height_clearance_meters=2.10,
            base_hourly_rate_paise=5000,
        )
        db_session.add(space)

        # 3. Add verified document
        doc = PropertyDocument(
            property_id=prop_id,
            document_type=DocumentTypeEnum.PROPERTY_TAX_RECEIPT,
            file_name="tax.pdf",
            s3_key="tax_key.pdf",
            content_type="application/pdf",
            file_size_bytes=2048,
            is_verified=True,
        )
        db_session.add(doc)
        await db_session.commit()

        # 4. Submit for review
        sub_resp = await client.post(f"/api/v1/properties/{prop_id}/submit-review", headers=headers)
        assert sub_resp.status_code == 200
        assert sub_resp.json()["status"] == "PENDING_REVIEW"

        # Check DB status
        stmt = select(PropertyAuthorization).where(PropertyAuthorization.property_id == prop_id)
        auth = (await db_session.execute(stmt)).scalar_one()
        assert auth.status == AuthorizationStatusEnum.PENDING_REVIEW


@pytest.mark.asyncio
async def test_submit_property_without_bays_or_documents_rejected(db_session):
    """Verify review submission is rejected with 422 if spaces or verified documents are missing."""
    _owner, headers = await _create_owner(db_session, "prereq_fail")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/properties",
            json={
                "title": "Empty Prop",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "Empty Road",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=headers,
        )
        prop_id = create_resp.json()["id"]

        # Attempt submit with 0 bays and 0 docs -> 422
        resp_no_bays = await client.post(f"/api/v1/properties/{prop_id}/submit-review", headers=headers)
        assert resp_no_bays.status_code == 422

        # Add bay, but still 0 documents
        await client.post(
            f"/api/v1/properties/{prop_id}/spaces",
            json={
                "space_label": "BAY-TEST",
                "space_type": "COVERED",
                "vehicle_category": "SEDAN",
                "length_meters": 4.80,
                "width_meters": 2.40,
                "height_clearance_meters": 2.10,
                "base_hourly_rate_paise": 5000,
            },
            headers=headers,
        )

        resp_no_docs = await client.post(f"/api/v1/properties/{prop_id}/submit-review", headers=headers)
        assert resp_no_docs.status_code == 422


@pytest.mark.asyncio
async def test_public_discovery_filter_and_fuzzing(db_session):
    """Verify that public discovery filter strictly excludes non-approved properties and fuzzing produces valid coordinates."""
    owner, _ = await _create_owner(db_session, "disc_test")

    # 1. Draft property
    p_draft = Property(
        owner_id=owner.id,
        title="Draft Spot",
        property_type=PropertyTypeEnum.RESIDENTIAL_DRIVEWAY,
        address_line="Draft Lane",
        city="Bengaluru",
        postal_code="560001",
        location=PropertyService.make_point_wkt(12.9716, 77.5946),
        is_active=False,
    )
    db_session.add(p_draft)
    await db_session.flush()
    db_session.add(PropertyAuthorization(property_id=p_draft.id, status=AuthorizationStatusEnum.DRAFT))

    # 2. Approved and active property
    p_app = Property(
        owner_id=owner.id,
        title="Approved Spot",
        property_type=PropertyTypeEnum.RESIDENTIAL_DRIVEWAY,
        address_line="Approved Lane",
        city="Bengaluru",
        postal_code="560001",
        location=PropertyService.make_point_wkt(12.9716, 77.5946),
        is_active=True,
    )
    db_session.add(p_app)
    await db_session.flush()
    db_session.add(PropertyAuthorization(property_id=p_app.id, status=AuthorizationStatusEnum.APPROVED))
    await db_session.commit()

    # Apply public discovery filter
    base_query = select(Property).where(Property.id.in_([p_draft.id, p_app.id]))
    filtered_query = PropertyService.apply_public_discovery_filter(base_query)
    results = list((await db_session.execute(filtered_query)).scalars().all())

    assert len(results) == 1
    assert results[0].id == p_app.id

    # Test coordinate fuzzing
    lat, lon = 12.9716, 77.5946
    fuzzed_lat, fuzzed_lon = PropertyService.fuzz_coordinates(lat, lon, offset_meters=100.0)
    assert abs(fuzzed_lat - lat) <= 0.002
    assert abs(fuzzed_lon - lon) <= 0.002
