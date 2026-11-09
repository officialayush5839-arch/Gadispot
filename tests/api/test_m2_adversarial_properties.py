"""Adversarial stress-test suite for Phase 03 Milestone 2: Backend Property, Inventory & Scheduling Engine.

Empirical verification covering:
1. Coordinate Boundaries: Extreme coordinates (lat ±90, lon ±180) vs out-of-bound (lat 90.001, lon 180.001, NaN, Inf).
2. Postal Code: Non-6-digit formats (5 digits, 7 digits, alphanumeric, spaces, SQLi, empty).
3. Review Submission State Machine:
   - 0 parking bays (422/400 failure)
   - 0 verified documents (422/400 failure)
   - Unverified documents (is_verified=False) (422/400 failure)
   - Already PENDING_REVIEW or APPROVED (409/400 conflict failure)
   - Successful transitions from DRAFT and REJECTED when prerequisites are met.
4. Public Discovery Leak Prevention:
   - Verify unapproved, draft, inactive, suspended, and pending properties are excluded.
   - Verify exact host coordinates are never leaked verbatim (coordinate fuzzing applied).
5. RBAC & Cross-Tenant Security:
   - Cross-owner tampering rejected with 403 Forbidden (IDOR prevention on property, spaces, schedules).
   - DRIVER role mutation attempts rejected with 403 Forbidden.
   - Unauthenticated requests rejected with 401 Unauthorized.
"""

import math
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


async def _create_test_owner(db_session, suffix="adv_owner") -> tuple[User, dict[str, str]]:
    """Helper to provision an active OWNER user with valid Bearer token."""
    phone = f"+9196{uuid.uuid4().hex[:8]}"
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


async def _create_test_driver(db_session) -> tuple[User, dict[str, str]]:
    """Helper to provision an active DRIVER user with valid Bearer token."""
    phone = f"+9195{uuid.uuid4().hex[:8]}"
    user = User(
        phone_number=phone,
        full_name="Adversarial Driver",
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


# =============================================================================
# Area 1: Coordinate Boundaries
# =============================================================================


@pytest.mark.asyncio
async def test_adversarial_coordinate_exact_boundaries(db_session):
    """Stress-test extreme boundary coordinates: North/South poles and Antimeridian."""
    _owner, headers = await _create_test_owner(db_session, "coords_exact")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Extreme 1: North Pole & Antimeridian (lat 90.0, lon 180.0)
        p1 = await client.post(
            "/api/v1/properties",
            json={
                "title": "North Pole Outpost",
                "property_type": "COMMERCIAL_BUILDING",
                "address_line": "90 North Pole Ave",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 90.0,
                "longitude": 180.0,
            },
            headers=headers,
        )
        assert p1.status_code == 201, f"Expected 201 for lat 90.0, lon 180.0, got: {p1.text}"
        data1 = p1.json()
        assert data1["latitude"] == pytest.approx(90.0, abs=1e-4)
        assert data1["longitude"] == pytest.approx(180.0, abs=1e-4)

        # Extreme 2: South Pole & Western Antimeridian (lat -90.0, lon -180.0)
        p2 = await client.post(
            "/api/v1/properties",
            json={
                "title": "South Pole Station",
                "property_type": "OPEN_PLOT",
                "address_line": "Amundsen-Scott Base",
                "city": "Bengaluru",
                "postal_code": "560002",
                "latitude": -90.0,
                "longitude": -180.0,
            },
            headers=headers,
        )
        assert p2.status_code == 201, f"Expected 201 for lat -90.0, lon -180.0, got: {p2.text}"
        data2 = p2.json()
        assert data2["latitude"] == pytest.approx(-90.0, abs=1e-4)
        assert data2["longitude"] == pytest.approx(-180.0, abs=1e-4)

        # Extreme 3: Equator and Prime Meridian (lat 0.0, lon 0.0)
        p3 = await client.post(
            "/api/v1/properties",
            json={
                "title": "Null Island Hub",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "Gulf of Guinea Station",
                "city": "Bengaluru",
                "postal_code": "560003",
                "latitude": 0.0,
                "longitude": 0.0,
            },
            headers=headers,
        )
        assert p3.status_code == 201, f"Expected 201 for lat 0.0, lon 0.0, got: {p3.text}"


@pytest.mark.asyncio
async def test_adversarial_coordinate_out_of_bounds_rejected(db_session):
    """Stress-test out-of-bounds coordinates (lat > 90, lat < -90, lon > 180, lon < -180)."""
    _, headers = await _create_test_owner(db_session, "coords_oob")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        invalid_coords = [
            (90.0001, 77.0, "Latitude slightly above 90"),
            (90.1, 77.0, "Latitude above 90"),
            (1000.0, 77.0, "Latitude grossly out of range"),
            (-90.0001, 77.0, "Latitude slightly below -90"),
            (-150.0, 77.0, "Latitude below -90"),
            (12.0, 180.0001, "Longitude slightly above 180"),
            (12.0, 180.5, "Longitude above 180"),
            (12.0, 360.0, "Longitude full circle"),
            (12.0, -180.0001, "Longitude slightly below -180"),
            (12.0, -9999.0, "Longitude grossly negative"),
        ]

        for lat, lon, desc in invalid_coords:
            resp = await client.post(
                "/api/v1/properties",
                json={
                    "title": f"Invalid Coord: {desc}",
                    "property_type": "RESIDENTIAL_DRIVEWAY",
                    "address_line": "123 Boundary Way",
                    "city": "Bengaluru",
                    "postal_code": "560001",
                    "latitude": lat,
                    "longitude": lon,
                },
                headers=headers,
            )
            assert resp.status_code == 422, f"Expected 422 for {desc} (lat={lat}, lon={lon}), got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_adversarial_coordinate_nan_inf_rejected(db_session):
    """Verify NaN and Infinity coordinates are strictly rejected."""
    _, headers = await _create_test_owner(db_session, "coords_nan_inf")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # String representations of NaN / Inf in JSON
        for val in ["NaN", "-NaN", "Infinity", "-Infinity", "inf", "-inf"]:
            resp = await client.post(
                "/api/v1/properties",
                json={
                    "title": "NaN Coord Test",
                    "property_type": "RESIDENTIAL_DRIVEWAY",
                    "address_line": "123 Float Test",
                    "city": "Bengaluru",
                    "postal_code": "560001",
                    "latitude": val,
                    "longitude": 77.5946,
                },
                headers=headers,
            )
            assert resp.status_code == 422, f"Expected 422 for latitude={val}, got: {resp.status_code}"

            resp_lon = await client.post(
                "/api/v1/properties",
                json={
                    "title": "NaN Lon Test",
                    "property_type": "RESIDENTIAL_DRIVEWAY",
                    "address_line": "123 Float Test",
                    "city": "Bengaluru",
                    "postal_code": "560001",
                    "latitude": 12.9716,
                    "longitude": val,
                },
                headers=headers,
            )
            assert resp_lon.status_code == 422, f"Expected 422 for longitude={val}, got: {resp_lon.status_code}"


@pytest.mark.asyncio
async def test_adversarial_coordinate_update_boundaries(db_session):
    """Verify coordinate boundary enforcement during property update mutations."""
    _, headers = await _create_test_owner(db_session, "coords_update")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create base property
        create_resp = await client.post(
            "/api/v1/properties",
            json={
                "title": "Updatable Coords",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "123 Update Rd",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=headers,
        )
        assert create_resp.status_code == 201
        prop_id = create_resp.json()["id"]

        # Valid extreme update: lat -90.0, lon 180.0
        up_valid = await client.put(
            f"/api/v1/properties/{prop_id}",
            json={"latitude": -90.0, "longitude": 180.0},
            headers=headers,
        )
        assert up_valid.status_code == 200
        assert up_valid.json()["latitude"] == pytest.approx(-90.0, abs=1e-4)
        assert up_valid.json()["longitude"] == pytest.approx(180.0, abs=1e-4)

        # Invalid update: lat 90.001 -> 422
        up_invalid_lat = await client.put(
            f"/api/v1/properties/{prop_id}",
            json={"latitude": 90.001},
            headers=headers,
        )
        assert up_invalid_lat.status_code == 422

        # Invalid update: lon -180.001 -> 422
        up_invalid_lon = await client.put(
            f"/api/v1/properties/{prop_id}",
            json={"longitude": -180.001},
            headers=headers,
        )
        assert up_invalid_lon.status_code == 422


# =============================================================================
# Area 2: Postal Code
# =============================================================================


@pytest.mark.asyncio
async def test_adversarial_postal_code_invalid_formats(db_session):
    """Stress-test postal code formats (5 digits, 7 digits, alphanumeric, spaces, SQLi)."""
    _, headers = await _create_test_owner(db_session, "postal_adv")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        invalid_postal_codes = [
            ("56010", "5 digits (too short)"),
            ("5601034", "7 digits (too long)"),
            ("056010", "6 digits with leading zero (invalid Indian PIN)"),
            ("000000", "All zeros"),
            ("56000A", "Trailing alpha character"),
            ("A56000", "Leading alpha character"),
            ("PIN123", "Alphanumeric string"),
            ("SW1A 1AA", "UK postcode format"),
            ("90210-1234", "US ZIP+4 format"),
            ("560 103", "Embedded space"),
            (" 560103", "Leading space"),
            ("560103 ", "Trailing space"),
            ("", "Empty string"),
            ("      ", "Whitespace only"),
            ("560103; DROP TABLE properties;--", "SQL Injection payload"),
            ("<script>alert(1)</script>", "XSS payload"),
            ("!@#$%^", "Punctuation symbols"),
        ]

        for code, desc in invalid_postal_codes:
            resp = await client.post(
                "/api/v1/properties",
                json={
                    "title": f"Postal Test: {desc}",
                    "property_type": "RESIDENTIAL_DRIVEWAY",
                    "address_line": "123 Postal St",
                    "city": "Bengaluru",
                    "postal_code": code,
                    "latitude": 12.9716,
                    "longitude": 77.5946,
                },
                headers=headers,
            )
            assert resp.status_code == 422, f"Expected 422 for postal code '{code}' ({desc}), got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_adversarial_postal_code_update_rejected(db_session):
    """Verify that updating an existing property with invalid postal code is strictly rejected."""
    _, headers = await _create_test_owner(db_session, "postal_up")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        p = await client.post(
            "/api/v1/properties",
            json={
                "title": "Valid Postal Prop",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "123 Postal St",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=headers,
        )
        assert p.status_code == 201
        prop_id = p.json()["id"]

        # Attempt to update to 5-digit postal code
        up_resp = await client.put(
            f"/api/v1/properties/{prop_id}",
            json={"postal_code": "56001"},
            headers=headers,
        )
        assert up_resp.status_code == 422


# =============================================================================
# Area 3: Review Submission State Machine
# =============================================================================


@pytest.mark.asyncio
async def test_adversarial_review_submission_zero_bays(db_session):
    """Attempt review submission on property with 0 parking bays (must fail with 4xx validation error)."""
    _, headers = await _create_test_owner(db_session, "sub_0_bays")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create property (0 bays, 0 docs)
        create_resp = await client.post(
            "/api/v1/properties",
            json={
                "title": "Zero Bay Property",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "123 Empty Bay Way",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=headers,
        )
        assert create_resp.status_code == 201
        prop_id = create_resp.json()["id"]

        # Attempt submit-review -> must fail with 422/400 (NO_SPACES_CONFIGURED)
        sub_resp = await client.post(f"/api/v1/properties/{prop_id}/submit-review", headers=headers)
        assert sub_resp.status_code in (400, 422), f"Expected 400 or 422 for 0 bays, got: {sub_resp.status_code}"
        err = sub_resp.json()
        assert err["code"] == "NO_SPACES_CONFIGURED"


@pytest.mark.asyncio
async def test_adversarial_review_submission_zero_verified_docs(db_session):
    """Attempt review submission with 1 bay but 0 documents (must fail with 4xx validation error)."""
    _, headers = await _create_test_owner(db_session, "sub_0_docs")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create property
        create_resp = await client.post(
            "/api/v1/properties",
            json={
                "title": "Zero Docs Property",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "123 No Docs Way",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=headers,
        )
        assert create_resp.status_code == 201
        prop_id = create_resp.json()["id"]

        # Add 1 parking space
        space_resp = await client.post(
            f"/api/v1/properties/{prop_id}/spaces",
            json={
                "space_label": "BAY-ADV-01",
                "space_type": "COVERED",
                "vehicle_category": "SEDAN",
                "length_meters": 5.0,
                "width_meters": 2.5,
                "height_clearance_meters": 2.2,
                "base_hourly_rate_paise": 6000,
            },
            headers=headers,
        )
        assert space_resp.status_code == 201

        # Attempt submit-review (has space, but 0 documents)
        sub_resp = await client.post(f"/api/v1/properties/{prop_id}/submit-review", headers=headers)
        assert sub_resp.status_code in (400, 422), f"Expected 400 or 422 for 0 docs, got: {sub_resp.status_code}"
        assert sub_resp.json()["code"] == "NO_VERIFIED_DOCUMENTS"


@pytest.mark.asyncio
async def test_adversarial_review_submission_unverified_docs_rejected(db_session):
    """Attempt review submission with documents that are NOT verified (is_verified=False) (must fail 4xx)."""
    _, headers = await _create_test_owner(db_session, "sub_unverified_docs")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create property
        create_resp = await client.post(
            "/api/v1/properties",
            json={
                "title": "Unverified Docs Property",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "123 Pending Doc Rd",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=headers,
        )
        prop_id = uuid.UUID(create_resp.json()["id"])

        # Add bay
        space = ParkingSpace(
            property_id=prop_id,
            space_label="BAY-1",
            vehicle_category=VehicleCategoryEnum.SEDAN,
            length_meters=5.0,
            width_meters=2.5,
            height_clearance_meters=2.2,
            base_hourly_rate_paise=5000,
        )
        db_session.add(space)

        # Add document with is_verified=False (unverified / pending)
        doc = PropertyDocument(
            property_id=prop_id,
            document_type=DocumentTypeEnum.ELECTRICITY_BILL,
            file_name="pending_bill.pdf",
            s3_key="pending_bill_key.pdf",
            content_type="application/pdf",
            file_size_bytes=1024,
            is_verified=False,
        )
        db_session.add(doc)
        await db_session.commit()

        # Attempt submit-review -> must fail with 422/400 (NO_VERIFIED_DOCUMENTS)
        sub_resp = await client.post(f"/api/v1/properties/{prop_id}/submit-review", headers=headers)
        assert sub_resp.status_code in (400, 422), f"Expected 400 or 422 for unverified docs, got: {sub_resp.status_code}"
        assert sub_resp.json()["code"] == "NO_VERIFIED_DOCUMENTS"


@pytest.mark.asyncio
async def test_adversarial_review_submission_already_pending_or_approved(db_session):
    """Attempt review submission when property is already in PENDING_REVIEW or APPROVED state (must fail 409/400)."""
    _, headers = await _create_test_owner(db_session, "sub_state_conflict")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create property
        create_resp = await client.post(
            "/api/v1/properties",
            json={
                "title": "State Conflict Property",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "123 Conflict Lane",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=headers,
        )
        prop_id = uuid.UUID(create_resp.json()["id"])

        # Add bay and verified document
        db_session.add(
            ParkingSpace(
                property_id=prop_id,
                space_label="BAY-CONF",
                vehicle_category=VehicleCategoryEnum.SEDAN,
                length_meters=5.0,
                width_meters=2.5,
                height_clearance_meters=2.2,
                base_hourly_rate_paise=5000,
            )
        )
        db_session.add(
            PropertyDocument(
                property_id=prop_id,
                document_type=DocumentTypeEnum.PROPERTY_TAX_RECEIPT,
                file_name="tax.pdf",
                s3_key="tax_key.pdf",
                content_type="application/pdf",
                file_size_bytes=2048,
                is_verified=True,
            )
        )
        await db_session.commit()

        # Submit first time -> transitions to PENDING_REVIEW
        first_sub = await client.post(f"/api/v1/properties/{prop_id}/submit-review", headers=headers)
        assert first_sub.status_code == 200
        assert first_sub.json()["status"] == "PENDING_REVIEW"

        # Attempt submit again while in PENDING_REVIEW -> must fail with 409/400 (ALREADY_SUBMITTED)
        second_sub = await client.post(f"/api/v1/properties/{prop_id}/submit-review", headers=headers)
        assert second_sub.status_code in (400, 409), f"Expected 409 or 400 for already submitted, got: {second_sub.status_code}"
        assert second_sub.json()["code"] == "ALREADY_SUBMITTED"

        # Manually transition authorization to APPROVED
        auth_stmt = select(PropertyAuthorization).where(PropertyAuthorization.property_id == prop_id)
        auth = (await db_session.execute(auth_stmt)).scalar_one()
        auth.status = AuthorizationStatusEnum.APPROVED
        await db_session.commit()

        # Attempt submit when APPROVED -> must fail with 409/400 (ALREADY_APPROVED)
        third_sub = await client.post(f"/api/v1/properties/{prop_id}/submit-review", headers=headers)
        assert third_sub.status_code in (400, 409), f"Expected 409 or 400 for already approved, got: {third_sub.status_code}"
        assert third_sub.json()["code"] == "ALREADY_APPROVED"


@pytest.mark.asyncio
async def test_adversarial_review_submission_transition_from_rejected(db_session):
    """Verify that a property in REJECTED state can successfully transition back to PENDING_REVIEW when resubmitted."""
    _, headers = await _create_test_owner(db_session, "resubmit_rejected")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/properties",
            json={
                "title": "Rejected Property Resubmission",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "123 Retry Way",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=headers,
        )
        prop_id = uuid.UUID(create_resp.json()["id"])

        # Configure bay & verified document
        db_session.add(
            ParkingSpace(
                property_id=prop_id,
                space_label="BAY-RETRY",
                vehicle_category=VehicleCategoryEnum.SEDAN,
                length_meters=5.0,
                width_meters=2.5,
                height_clearance_meters=2.2,
                base_hourly_rate_paise=5000,
            )
        )
        db_session.add(
            PropertyDocument(
                property_id=prop_id,
                document_type=DocumentTypeEnum.PROPERTY_TAX_RECEIPT,
                file_name="tax.pdf",
                s3_key="tax_key.pdf",
                content_type="application/pdf",
                file_size_bytes=2048,
                is_verified=True,
            )
        )

        # Set status to REJECTED (simulating operations rejection)
        auth_stmt = select(PropertyAuthorization).where(PropertyAuthorization.property_id == prop_id)
        auth = (await db_session.execute(auth_stmt)).scalar_one()
        auth.status = AuthorizationStatusEnum.REJECTED
        auth.rejection_reason_code = "DOC_BLURRY"
        auth.reviewer_notes = "Please upload a clearer tax receipt."
        await db_session.commit()

        # Space owner resubmits -> successful transition to PENDING_REVIEW
        resub = await client.post(f"/api/v1/properties/{prop_id}/submit-review", headers=headers)
        assert resub.status_code == 200
        assert resub.json()["status"] == "PENDING_REVIEW"

        # Verify DB updated
        await db_session.refresh(auth)
        assert auth.status == AuthorizationStatusEnum.PENDING_REVIEW


# =============================================================================
# Area 4: Public Discovery Leak Prevention
# =============================================================================


@pytest.mark.asyncio
async def test_adversarial_discovery_exclusion_gatekeeper(db_session):
    """Verify that unapproved, draft, inactive, or suspended properties are strictly excluded from public discovery queries."""
    owner, _ = await _create_test_owner(db_session, "disc_gatekeeper")

    # Helper to create property in DB with specific status and is_active flag
    async def _make_property(title: str, is_active: bool, auth_status: AuthorizationStatusEnum) -> Property:
        p = Property(
            owner_id=owner.id,
            title=title,
            property_type=PropertyTypeEnum.RESIDENTIAL_DRIVEWAY,
            address_line="123 Discovery Test St",
            city="Bengaluru",
            postal_code="560001",
            location=PropertyService.make_point_wkt(12.9716, 77.5946),
            is_active=is_active,
        )
        db_session.add(p)
        await db_session.flush()
        db_session.add(PropertyAuthorization(property_id=p.id, status=auth_status))
        await db_session.commit()
        return p

    # 1. DRAFT, inactive
    p_draft = await _make_property("Draft Inactive", is_active=False, auth_status=AuthorizationStatusEnum.DRAFT)
    # 2. PENDING_REVIEW, inactive
    p_pending = await _make_property("Pending Inactive", is_active=False, auth_status=AuthorizationStatusEnum.PENDING_REVIEW)
    # 3. REJECTED, inactive
    p_rejected = await _make_property("Rejected Inactive", is_active=False, auth_status=AuthorizationStatusEnum.REJECTED)
    # 4. SUSPENDED, inactive
    p_suspended = await _make_property("Suspended Inactive", is_active=False, auth_status=AuthorizationStatusEnum.SUSPENDED)
    # 5. APPROVED, but is_active=False (owner paused listing)
    p_paused = await _make_property("Approved but Inactive", is_active=False, auth_status=AuthorizationStatusEnum.APPROVED)
    # 6. DRAFT, but is_active=True (tampered active flag on draft)
    p_tampered = await _make_property("Draft Tampered Active", is_active=True, auth_status=AuthorizationStatusEnum.DRAFT)
    # 7. APPROVED, and is_active=True (the ONLY discoverable property)
    p_discoverable = await _make_property("Approved and Active", is_active=True, auth_status=AuthorizationStatusEnum.APPROVED)

    all_ids = [
        p_draft.id,
        p_pending.id,
        p_rejected.id,
        p_suspended.id,
        p_paused.id,
        p_tampered.id,
        p_discoverable.id,
    ]

    base_query = select(Property).where(Property.id.in_(all_ids))
    filtered_query = PropertyService.apply_public_discovery_filter(base_query)
    results = list((await db_session.execute(filtered_query)).scalars().all())

    result_ids = {r.id for r in results}

    # CRITICAL: Only p_discoverable must be discovered
    assert p_discoverable.id in result_ids, "Approved and active property must be discoverable."
    assert p_draft.id not in result_ids, "DRAFT property leaked into discovery!"
    assert p_pending.id not in result_ids, "PENDING_REVIEW property leaked into discovery!"
    assert p_rejected.id not in result_ids, "REJECTED property leaked into discovery!"
    assert p_suspended.id not in result_ids, "SUSPENDED property leaked into discovery!"
    assert p_paused.id not in result_ids, "Inactive APPROVED property leaked into discovery!"
    assert p_tampered.id not in result_ids, "DRAFT property with active=True leaked into discovery!"
    assert len(results) == 1, f"Expected exactly 1 discoverable property, got {len(results)}"


@pytest.mark.asyncio
async def test_adversarial_discovery_coordinate_fuzzing(db_session):
    """Verify coordinate fuzzing prevents exact host address leakage across edge cases."""
    test_coordinates = [
        (12.971598, 77.594562, "Bengaluru Central"),
        (28.613939, 77.209021, "New Delhi Connaught Place"),
        (19.076090, 72.877426, "Mumbai Nariman Point"),
        (0.000000, 0.000000, "Equator & Prime Meridian"),
        (85.000000, 175.000000, "Near North Pole"),
        (-85.000000, -175.000000, "Near South Pole"),
    ]

    for exact_lat, exact_lon, label in test_coordinates:
        fuzzed_lat, fuzzed_lon = PropertyService.fuzz_coordinates(exact_lat, exact_lon, offset_meters=100.0)

        # 1. Exact coordinates must NEVER match verbatim (prevent precise stalking/leakage)
        assert (fuzzed_lat != exact_lat) or (fuzzed_lon != exact_lon), f"Exact coordinates leaked verbatim for {label}!"

        # 2. Coordinates must remain within valid WGS 84 bounds
        assert -90.0 <= fuzzed_lat <= 90.0, f"Fuzzed latitude {fuzzed_lat} out of bounds for {label}"
        assert -180.0 <= fuzzed_lon <= 180.0, f"Fuzzed longitude {fuzzed_lon} out of bounds for {label}"

        # 3. Fuzzing displacement must be within expected approximate neighborhood radius (<= 0.005 degrees)
        lat_diff = abs(fuzzed_lat - exact_lat)
        lon_diff = abs(fuzzed_lon - exact_lon)
        assert lat_diff <= 0.005, f"Latitude displacement {lat_diff} too large for {label}"
        assert lon_diff <= 0.005, f"Longitude displacement {lon_diff} too large for {label}"


# =============================================================================
# Area 5: RBAC & Cross-Tenant Security
# =============================================================================


@pytest.mark.asyncio
async def test_adversarial_cross_owner_tampering_prevented(db_session):
    """Verify Owner B cannot update, delete, submit, or add sub-resources to Owner A's property (IDOR prevention)."""
    _owner_a, headers_a = await _create_test_owner(db_session, "idor_victim_a")
    _owner_b, headers_b = await _create_test_owner(db_session, "idor_attacker_b")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Owner A creates Property A
        prop_a = await client.post(
            "/api/v1/properties",
            json={
                "title": "Owner A Sanctuary",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "100 Sovereign Lane",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=headers_a,
        )
        assert prop_a.status_code == 201
        prop_a_id = prop_a.json()["id"]

        # Owner A adds space
        space_a = await client.post(
            f"/api/v1/properties/{prop_a_id}/spaces",
            json={
                "space_label": "BAY-A1",
                "space_type": "COVERED",
                "vehicle_category": "SEDAN",
                "length_meters": 5.0,
                "width_meters": 2.5,
                "height_clearance_meters": 2.2,
                "base_hourly_rate_paise": 5000,
            },
            headers=headers_a,
        )
        assert space_a.status_code == 201
        space_a_id = space_a.json()["id"]

        # Attack 1: Owner B attempts to update Property A
        atk1 = await client.put(
            f"/api/v1/properties/{prop_a_id}",
            json={"title": "Hacked Sanctuary"},
            headers=headers_b,
        )
        assert atk1.status_code == 403, f"Owner B could update Property A! Got {atk1.status_code}"

        # Attack 2: Owner B attempts to submit Property A for review
        atk2 = await client.post(
            f"/api/v1/properties/{prop_a_id}/submit-review",
            headers=headers_b,
        )
        assert atk2.status_code == 403, f"Owner B could submit Property A! Got {atk2.status_code}"

        # Attack 3: Owner B attempts to add a bay to Property A
        atk3 = await client.post(
            f"/api/v1/properties/{prop_a_id}/spaces",
            json={
                "space_label": "BAY-ROGUE",
                "space_type": "OPEN",
                "vehicle_category": "HATCHBACK",
                "length_meters": 4.0,
                "width_meters": 2.0,
                "height_clearance_meters": 2.0,
                "base_hourly_rate_paise": 1000,
            },
            headers=headers_b,
        )
        assert atk3.status_code == 403, f"Owner B could add a bay to Property A! Got {atk3.status_code}"

        # Attack 4: Owner B attempts to update Owner A's parking space
        atk4 = await client.put(
            f"/api/v1/spaces/{space_a_id}",
            json={"space_label": "BAY-HIJACKED", "base_hourly_rate_paise": 100},
            headers=headers_b,
        )
        assert atk4.status_code == 403, f"Owner B could update Space A! Got {atk4.status_code}"

        # Attack 5: Owner B attempts to add operating schedule to Property A
        atk5 = await client.post(
            f"/api/v1/properties/{prop_a_id}/operating-hours",
            json={
                "day_of_week": 1,
                "start_time": "08:00:00",
                "end_time": "20:00:00",
            },
            headers=headers_b,
        )
        assert atk5.status_code == 403, f"Owner B could add operating schedule to Property A! Got {atk5.status_code}"

        # Attack 6: Owner B attempts to add blackout to Property A
        atk6 = await client.post(
            f"/api/v1/properties/{prop_a_id}/blackouts",
            json={
                "start_time": "2026-12-01T08:00:00Z",
                "end_time": "2026-12-01T20:00:00Z",
                "reason": "Hostile Blackout",
            },
            headers=headers_b,
        )
        assert atk6.status_code == 403, f"Owner B could add blackout to Property A! Got {atk6.status_code}"

        # Attack 7: Owner B attempts to add blackout directly to Space A
        atk7 = await client.post(
            f"/api/v1/spaces/{space_a_id}/blackouts",
            json={
                "start_time": "2026-12-01T08:00:00Z",
                "end_time": "2026-12-01T20:00:00Z",
                "reason": "Hostile Bay Blackout",
            },
            headers=headers_b,
        )
        assert atk7.status_code == 403, f"Owner B could add blackout to Space A! Got {atk7.status_code}"


@pytest.mark.asyncio
async def test_adversarial_driver_role_restrictions(db_session):
    """Verify that users with DRIVER role cannot create, modify, or submit properties or spaces."""
    owner, owner_headers = await _create_test_owner(db_session, "driver_target_owner")
    _driver, driver_headers = await _create_test_driver(db_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Driver attempts to create property -> 403
        d1 = await client.post(
            "/api/v1/properties",
            json={
                "title": "Driver Illegitimate Property",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "123 Driver Rd",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=driver_headers,
        )
        assert d1.status_code == 403, f"Driver was able to create property! Got {d1.status_code}"

        # Owner creates legitimate property
        legit_prop = await client.post(
            "/api/v1/properties",
            json={
                "title": "Legit Property",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "123 Legit St",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            headers=owner_headers,
        )
        assert legit_prop.status_code == 201
        prop_id = legit_prop.json()["id"]

        # 2. Driver attempts to update property -> 403
        d2 = await client.put(
            f"/api/v1/properties/{prop_id}",
            json={"title": "Driver Updated"},
            headers=driver_headers,
        )
        assert d2.status_code == 403, f"Driver was able to update property! Got {d2.status_code}"

        # 3. Driver attempts to submit property for review -> 403
        d3 = await client.post(
            f"/api/v1/properties/{prop_id}/submit-review",
            headers=driver_headers,
        )
        assert d3.status_code == 403, f"Driver was able to submit review! Got {d3.status_code}"

        # 4. Driver attempts to create parking space -> 403
        d4 = await client.post(
            f"/api/v1/properties/{prop_id}/spaces",
            json={
                "space_label": "DRIVER-BAY",
                "space_type": "COVERED",
                "vehicle_category": "SEDAN",
                "length_meters": 5.0,
                "width_meters": 2.5,
                "height_clearance_meters": 2.2,
                "base_hourly_rate_paise": 5000,
            },
            headers=driver_headers,
        )
        assert d4.status_code == 403, f"Driver was able to create space! Got {d4.status_code}"

        # 5. Driver attempts to add operating schedule -> 403
        d5 = await client.post(
            f"/api/v1/properties/{prop_id}/operating-hours",
            json={
                "day_of_week": 0,
                "start_time": "09:00:00",
                "end_time": "18:00:00",
            },
            headers=driver_headers,
        )
        assert d5.status_code == 403, f"Driver was able to add operating schedule! Got {d5.status_code}"

        # 6. Driver attempts to add property blackout -> 403
        d6 = await client.post(
            f"/api/v1/properties/{prop_id}/blackouts",
            json={
                "start_time": "2026-11-20T09:00:00Z",
                "end_time": "2026-11-20T18:00:00Z",
                "reason": "Driver block",
            },
            headers=driver_headers,
        )
        assert d6.status_code == 403, f"Driver was able to add blackout! Got {d6.status_code}"


@pytest.mark.asyncio
async def test_adversarial_unauthenticated_requests_rejected(db_session):
    """Verify that unauthenticated callers (no Bearer token) are rejected with 401 Unauthorized across all endpoints."""
    dummy_uuid = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create property
        r1 = await client.post(
            "/api/v1/properties",
            json={
                "title": "Anon Property",
                "property_type": "RESIDENTIAL_DRIVEWAY",
                "address_line": "123 Anon St",
                "city": "Bengaluru",
                "postal_code": "560001",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
        )
        assert r1.status_code == 401

        # 2. List caller's properties
        r2 = await client.get("/api/v1/properties")
        assert r2.status_code == 401

        # 3. Update property
        r3 = await client.put(f"/api/v1/properties/{dummy_uuid}", json={"title": "Hacked"})
        assert r3.status_code == 401

        # 4. Submit review
        r4 = await client.post(f"/api/v1/properties/{dummy_uuid}/submit-review")
        assert r4.status_code == 401

        # 5. Create parking space
        r5 = await client.post(
            f"/api/v1/properties/{dummy_uuid}/spaces",
            json={
                "space_label": "BAY-1",
                "space_type": "COVERED",
                "vehicle_category": "SEDAN",
                "length_meters": 5.0,
                "width_meters": 2.5,
                "height_clearance_meters": 2.2,
                "base_hourly_rate_paise": 5000,
            },
        )
        assert r5.status_code == 401

        # 6. Update parking space
        r6 = await client.put(f"/api/v1/spaces/{dummy_uuid}", json={"space_label": "NEW"})
        assert r6.status_code == 401

        # 7. Add operating hours
        r7 = await client.post(
            f"/api/v1/properties/{dummy_uuid}/operating-hours",
            json={"day_of_week": 0, "start_time": "08:00:00", "end_time": "18:00:00"},
        )
        assert r7.status_code == 401

        # 8. Add blackout
        r8 = await client.post(
            f"/api/v1/properties/{dummy_uuid}/blackouts",
            json={"start_time": "2026-11-20T09:00:00Z", "end_time": "2026-11-20T18:00:00Z"},
        )
        assert r8.status_code == 401
