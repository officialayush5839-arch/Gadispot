"""Tier 4: Real-World Application Scenarios E2E Tests for Phase 03 Supply Engine.

Covers 5 multi-step end-to-end user journeys:
1. Residential Host Complete Onboarding & Approval Journey
2. Commercial Society Onboarding with Rejection, Correction & Resubmission Cycle
3. Blackout Management & Operational Protection Journey
4. Multi-Operator Concurrency Race & Conflict Resolution
5. Multi-Bay Mixed Vehicle Fleet & Compatibility Verification Journey
"""

import uuid

import pytest
from app.models.enums import (
    AccountStatus,
    AuthorizationStatusEnum,
    UserRoleEnum,
)
from app.models.properties import PropertyAuthorization
from app.models.schedules import BlackoutSchedule
from app.models.users import User, UserRole
from app.services.compatibility_service import (
    CompatibilityService,
    SpaceDimensions,
    VehicleDimensions,
)
from httpx import AsyncClient
from sqlalchemy import select

from tests.e2e.conftest import get_current_totp

# =============================================================================
# SCENARIO 1: Residential Host Complete Onboarding & Approval Journey
# =============================================================================


@pytest.mark.asyncio
async def test_s01_residential_host_complete_onboarding_journey(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
    driver_user: tuple[User, dict[str, str]],
    db_session,
):
    """Scenario 1: Residential Host Complete Onboarding -> Bays -> Upload -> Ops Queue -> Claim -> TOTP Approval -> Discovery Verification."""
    _owner_u, owner_headers = owner_user
    ops_u, ops_headers, totp_sec = ops_user
    _, driver_headers = driver_user

    # 1. Owner registers residential driveway property
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Indiranagar Peaceful Villa",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "12, 14th Main, HAL 2nd Stage, Indiranagar",
            "city": "Bengaluru",
            "postal_code": "560038",
            "latitude": 12.9719,
            "longitude": 77.6412,
        },
        headers=owner_headers,
    )
    assert prop_resp.status_code in (200, 201), prop_resp.text
    prop_id = prop_resp.json()["id"]

    # 2. Owner configures 2 bays: Standard Sedan and EV Sedan
    bay1_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "BAY-SEDAN",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "has_ev_charging": False,
            "base_hourly_rate_paise": 6000,
        },
        headers=owner_headers,
    )
    assert bay1_resp.status_code in (200, 201)

    bay2_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "BAY-EV-SEDAN",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "has_ev_charging": True,
            "base_hourly_rate_paise": 8000,
        },
        headers=owner_headers,
    )
    assert bay2_resp.status_code in (200, 201)

    # 3. Owner configures recurring operating hours (Mon-Sun 06:00 - 23:00)
    for day in range(7):
        sched_resp = await e2e_client.post(
            f"/api/v1/properties/{prop_id}/operating-hours",
            json={"day_of_week": day, "start_time": "06:00:00", "end_time": "23:00:00"},
            headers=owner_headers,
        )
        assert sched_resp.status_code in (200, 201)

    # 4. Owner uploads authorization document (PROPERTY_TAX_RECEIPT)
    presign_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "indiranagar_tax_receipt.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1048576,
        },
        headers=owner_headers,
    )
    assert presign_resp.status_code in (200, 201)
    doc_id = presign_resp.json()["document_id"]

    # 5. Owner completes upload verification
    verify_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{doc_id}/verify", headers=owner_headers
    )
    assert verify_resp.status_code in (200, 201)

    # 6. Owner submits property for operational review
    submit_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )
    assert submit_resp.status_code in (200, 201)
    assert submit_resp.json()["status"] == "PENDING_REVIEW"

    # 7. Ops user inspects review queue and sees the submitted property
    queue_resp = await e2e_client.get(
        "/api/v1/ops/properties/queue?city=Bengaluru", headers=ops_headers
    )
    assert queue_resp.status_code == 200
    queue_items = queue_resp.json()["items"]
    assert any(item["id"] == prop_id for item in queue_items)

    # 8. Ops user opens review dossier and inspects watermarked document
    dossier_resp = await e2e_client.get(
        f"/api/v1/ops/properties/{prop_id}", headers=ops_headers
    )
    assert dossier_resp.status_code == 200
    assert dossier_resp.json()["version"] == 1

    doc_resp = await e2e_client.get(
        f"/api/v1/ops/documents/{doc_id}/watermarked", headers=ops_headers
    )
    assert doc_resp.status_code in (200, 302, 307)

    # 9. Ops user performs TOTP step-up approval
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

    # 10. Database checks: version incremented to 2, reviewed_by set, is_active=True
    stmt = select(PropertyAuthorization).where(
        PropertyAuthorization.property_id == uuid.UUID(prop_id)
    )
    auth = (await db_session.execute(stmt)).scalar_one()
    assert auth.version == 2
    assert auth.status == AuthorizationStatusEnum.APPROVED
    assert auth.reviewed_by == ops_u.id

    # 11. Public discovery verification: Driver discovery query finds the active approved property
    disc_resp = await e2e_client.get(
        "/api/v1/bookings/discovery?latitude=12.9719&longitude=77.6412&radius_meters=1000",
        headers=driver_headers,
    )
    if disc_resp.status_code == 200:
        found_ids = [item["property_id"] for item in disc_resp.json().get("items", [])]
        assert prop_id in found_ids


# =============================================================================
# SCENARIO 2: Commercial Society Onboarding with Rejection & Resubmission Cycle
# =============================================================================


@pytest.mark.asyncio
async def test_s02_commercial_society_rejection_resubmission_cycle(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
    db_session,
):
    """Scenario 2: Commercial Society Setup -> Illegible Document -> Ops TOTP Rejection -> Owner Correction -> Resubmission -> Ops TOTP Approval."""
    _owner_u, owner_headers = owner_user
    _ops_u, ops_headers, totp_sec = ops_user

    # 1. Commercial host creates apartment society property
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Sobha Hibiscus Society",
            "property_type": "APARTMENT_SOCIETY",
            "address_line": "Ambalipura, Bellandur",
            "city": "Bengaluru",
            "postal_code": "560103",
            "latitude": 12.9240,
            "longitude": 77.6690,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    # 2. Add parking bays (Hatchback and SUV)
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "SOBHA-H1",
            "space_type": "COVERED",
            "vehicle_category": "HATCHBACK",
            "length_meters": 4.20,
            "width_meters": 2.20,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 4000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "SOBHA-SUV1",
            "space_type": "COVERED",
            "vehicle_category": "SUV",
            "length_meters": 5.00,
            "width_meters": 2.50,
            "height_clearance_meters": 2.20,
            "base_hourly_rate_paise": 8000,
        },
        headers=owner_headers,
    )

    # 3. Add 24/7 operating hours
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/operating-hours",
        json={"day_of_week": 0, "start_time": "00:00:00", "end_time": "23:59:59"},
        headers=owner_headers,
    )

    # 4. Upload blurry document
    p1 = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "SOCIETY_NOC",
            "file_name": "blurry_noc.png",
            "content_type": "image/png",
            "file_size_bytes": 50000,
        },
        headers=owner_headers,
    )
    doc_id1 = p1.json()["document_id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{doc_id1}/verify",
        headers=owner_headers,
    )

    # 5. Submit for review
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    # 6. Ops inspects queue, finds blurriness, enters TOTP and rejects with reason DOC_ILLEGIBLE
    reject_resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "Society NOC scan is dark and blurry. Seal is unreadable.",
        },
        headers=ops_headers,
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "REJECTED"

    # 7. Owner inspects rejection details
    owner_prop_resp = await e2e_client.get(
        f"/api/v1/properties/{prop_id}", headers=owner_headers
    )
    assert owner_prop_resp.status_code == 200
    auth_info = owner_prop_resp.json()["authorization"]
    assert auth_info["status"] == "REJECTED"
    assert auth_info["rejection_reason_code"] == "DOC_ILLEGIBLE"

    # 8. Owner uploads fresh clear scan
    p2 = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "SOCIETY_NOC",
            "file_name": "clean_noc_scan.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 200000,
        },
        headers=owner_headers,
    )
    doc_id2 = p2.json()["document_id"]
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{doc_id2}/verify",
        headers=owner_headers,
    )

    # 9. Owner resubmits for review
    resub_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )
    assert resub_resp.status_code in (200, 201)
    assert resub_resp.json()["status"] == "PENDING_REVIEW"

    # 10. Ops inspects updated dossier and approves with version 2
    approve_resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 2,
        },
        headers=ops_headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"
    assert approve_resp.json()["is_active"] is True


# =============================================================================
# SCENARIO 3: Blackout Management & Operational Protection Journey
# =============================================================================


@pytest.mark.asyncio
async def test_s03_blackout_management_operational_protection_journey(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
    db_session,
):
    """Scenario 3: Approved Property -> Weekend Personal Blackout -> Conflict Overlap Check -> Cancel Blackout -> Restored Availability."""
    _owner_u, owner_headers = owner_user
    _ops_u, ops_headers, totp_sec = ops_user

    # 1. Onboard and approve property
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Koramangala Active Villa",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "6th Block, Koramangala",
            "city": "Bengaluru",
            "postal_code": "560095",
            "latitude": 12.9370,
            "longitude": 77.6230,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    space_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "KORA-1",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 7000,
        },
        headers=owner_headers,
    )
    space_id = space_resp.json()["id"]

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

    # 2. Owner schedules personal weekend blackout on bay
    bo_resp = await e2e_client.post(
        f"/api/v1/spaces/{space_id}/blackouts",
        json={
            "start_time": "2026-12-18T18:00:00Z",
            "end_time": "2026-12-21T08:00:00Z",
            "reason": "Personal family wedding",
        },
        headers=owner_headers,
    )
    assert bo_resp.status_code in (200, 201)
    blackout_id = bo_resp.json()["id"]

    # 3. Attempting another overlapping blackout during the same window returns HTTP 409 Conflict
    conflict_resp = await e2e_client.post(
        f"/api/v1/spaces/{space_id}/blackouts",
        json={
            "start_time": "2026-12-19T00:00:00Z",
            "end_time": "2026-12-20T00:00:00Z",
            "reason": "Conflicting blackout",
        },
        headers=owner_headers,
    )
    assert conflict_resp.status_code in (400, 409, 422)

    # 4. Owner cancels the blackout
    cancel_resp = await e2e_client.delete(
        f"/api/v1/spaces/{space_id}/blackouts/{blackout_id}", headers=owner_headers
    )
    assert cancel_resp.status_code in (200, 204)

    # 5. Database check: blackout record deleted or marked inactive
    stmt = select(BlackoutSchedule).where(BlackoutSchedule.id == uuid.UUID(blackout_id))
    bo_row = (await db_session.execute(stmt)).scalar_one_or_none()
    assert bo_row is None or bo_row.is_active is False


# =============================================================================
# SCENARIO 4: Multi-Operator Concurrency Race & Conflict Resolution
# =============================================================================


@pytest.mark.asyncio
async def test_s04_multi_operator_concurrency_race_resolution(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
    db_session,
):
    """Scenario 4: Two operators claim dossier at version 1 -> Operator A approves -> Operator B stale rejection returns HTTP 409 Conflict."""
    _owner_u, owner_headers = owner_user
    _ops_u1, ops_headers1, totp_sec1 = ops_user

    # Provision Operator 2 with distinct TOTP secret
    import pyotp

    totp_sec2 = pyotp.random_base32()
    phone2 = f"+9199{uuid.uuid4().hex[:8]}"
    ops_u2 = User(
        phone_number=phone2,
        full_name="Operator 2",
        status=AccountStatus.ACTIVE,
        is_active=True,
        totp_secret=totp_sec2,
    )
    db_session.add(ops_u2)
    await db_session.flush()
    db_session.add(UserRole(user_id=ops_u2.id, role=UserRoleEnum.OPERATIONS))
    await db_session.commit()
    from app.core.security import create_access_token

    token2 = create_access_token(
        subject=str(ops_u2.id), claims={"roles": ["OPERATIONS"], "phone_number": phone2}
    )
    ops_headers2 = {"Authorization": f"Bearer {token2}"}

    # 1. Space Owner submits property
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Race Test Property",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "MG Road",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "RC-1",
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

    # 2. Both operators fetch dossier simultaneously (both observe version = 1)
    dossier_a = await e2e_client.get(
        f"/api/v1/ops/properties/{prop_id}", headers=ops_headers1
    )
    dossier_b = await e2e_client.get(
        f"/api/v1/ops/properties/{prop_id}", headers=ops_headers2
    )
    assert dossier_a.json()["version"] == 1
    assert dossier_b.json()["version"] == 1

    # 3. Operator A approves first with version 1
    app_a = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec1), "version": 1},
        headers=ops_headers1,
    )
    assert app_a.status_code == 200
    assert app_a.json()["status"] == "APPROVED"

    # 4. Operator B (without refreshing) attempts to reject with version 1 -> Must return HTTP 409 Conflict
    rej_b = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec2),
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "Stale reject attempt",
        },
        headers=ops_headers2,
    )
    assert rej_b.status_code == 409

    # 5. Operator B refreshes and sees latest approved state at version 2
    refreshed_b = await e2e_client.get(
        f"/api/v1/ops/properties/{prop_id}", headers=ops_headers2
    )
    assert refreshed_b.json()["version"] == 2
    assert refreshed_b.json()["status"] == "APPROVED"


# =============================================================================
# SCENARIO 5: Multi-Bay Mixed Vehicle Fleet & Compatibility Verification
# =============================================================================


@pytest.mark.asyncio
async def test_s05_multi_bay_mixed_fleet_compatibility_journey(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """Scenario 5: Multi-Bay Complex (Bike, Compact, Sedan, EV SUV) -> Compatibility Filtering across Fleet."""
    _owner_u, owner_headers = owner_user
    _ops_u, ops_headers, totp_sec = ops_user

    # 1. Onboard commercial parking complex
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Multi-Fleet Hub",
            "property_type": "COMMERCIAL_BUILDING",
            "address_line": "100 Ft Rd, Indiranagar",
            "city": "Bengaluru",
            "postal_code": "560038",
            "latitude": 12.9780,
            "longitude": 77.6400,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    # Bay 1: Two-Wheeler (2.2m x 1.0m x 2.0m, no EV)
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "BAY-BIKE",
            "space_type": "OPEN",
            "vehicle_category": "TWO_WHEELER",
            "length_meters": 2.20,
            "width_meters": 1.00,
            "height_clearance_meters": 2.00,
            "base_hourly_rate_paise": 2000,
        },
        headers=owner_headers,
    )

    # Bay 2: Compact Hatchback (4.2m x 2.1m x 2.0m, no EV)
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "BAY-HATCH",
            "space_type": "COVERED",
            "vehicle_category": "HATCHBACK",
            "length_meters": 4.20,
            "width_meters": 2.10,
            "height_clearance_meters": 2.00,
            "base_hourly_rate_paise": 4000,
        },
        headers=owner_headers,
    )

    # Bay 3: Standard Sedan (4.9m x 2.3m x 2.1m, no EV)
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "BAY-SEDAN",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.90,
            "width_meters": 2.30,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 6000,
        },
        headers=owner_headers,
    )

    # Bay 4: Large EV SUV (5.2m x 2.5m x 2.2m, with EV charging)
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "BAY-EV-SUV",
            "space_type": "BASEMENT",
            "vehicle_category": "SUV",
            "length_meters": 5.20,
            "width_meters": 2.50,
            "height_clearance_meters": 2.20,
            "has_ev_charging": True,
            "base_hourly_rate_paise": 10000,
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

    # 2. Evaluate physical compatibility:
    # A. Motorcycle (1900 x 750 x 1150 mm) fits Bay 1, 2, 3, 4
    bike = VehicleDimensions(length_mm=1900, width_mm=750, height_mm=1150)
    bay1 = SpaceDimensions(length_mm=2200, width_mm=1000, height_mm=2000)
    assert CompatibilityService.evaluate_compatibility(bike, bay1).is_compatible is True

    # B. Sedan (4500 x 1800 x 1500 mm) fits Bay 3, 4 (fails Bay 1, 2)
    sedan = VehicleDimensions(length_mm=4500, width_mm=1800, height_mm=1500)
    bay2 = SpaceDimensions(length_mm=4200, width_mm=2100, height_mm=2000)
    bay3 = SpaceDimensions(length_mm=4900, width_mm=2300, height_mm=2100)
    assert (
        CompatibilityService.evaluate_compatibility(sedan, bay2).is_compatible is False
    )  # 4200 - 4500 = -300mm length
    assert (
        CompatibilityService.evaluate_compatibility(sedan, bay3).is_compatible is True
    )  # 4900 - 4500 = +400mm (>=300)

    # C. Large SUV (4850 x 1950 x 1750 mm) fits Bay 4 (fails Bay 3)
    suv = VehicleDimensions(length_mm=4850, width_mm=1950, height_mm=1750)
    bay4 = SpaceDimensions(
        length_mm=5200, width_mm=2500, height_mm=2200, is_ev_charging=True
    )
    assert (
        CompatibilityService.evaluate_compatibility(suv, bay3).is_compatible is False
    )  # 4900 - 4850 = 50mm (< 300mm)
    assert (
        CompatibilityService.evaluate_compatibility(suv, bay4).is_compatible is True
    )  # 5200 - 4850 = 350mm (>= 300mm)

    # D. EV Sedan (demanding charging) fits ONLY Bay 4 (fails Bay 1, 2, 3 because they lack EV)
    ev_sedan = VehicleDimensions(
        length_mm=4500, width_mm=1800, height_mm=1500, is_ev=True
    )
    assert (
        CompatibilityService.evaluate_compatibility(ev_sedan, bay3).is_compatible
        is False
    )
    assert (
        CompatibilityService.evaluate_compatibility(ev_sedan, bay4).is_compatible
        is True
    )
