"""Tier 3: Cross-Feature Pairwise Combinations E2E Tests for Phase 03 Supply Engine.

Covers combinatorial pairwise interactions across the 5 dimensions:
1. Property Types: RESIDENTIAL_DRIVEWAY, APARTMENT_SOCIETY, COMMERCIAL_BUILDING, OPEN_PLOT
2. Vehicle Categories: TWO_WHEELER, HATCHBACK, SEDAN, SUV, EV_FOUR_WHEELER, EV_TWO_WHEELER
3. EV Flags: has_ev_charging (True / False) × driver_req_ev (True / False)
4. Operating Schedules: 24/7, Business hours (09:00 - 18:00), Weekend-only (Sat - Sun), Partial weekday
5. Review Decisions: APPROVED vs REJECTED with various structured reason codes
"""

import pytest
from app.models.users import User
from app.services.compatibility_service import (
    CompatibilityService,
    SpaceDimensions,
    VehicleDimensions,
)
from httpx import AsyncClient

from tests.e2e.conftest import get_current_totp

# =============================================================================
# Helper: Setup property with bay, schedule, document and submit for review
# =============================================================================


async def setup_property_for_review(
    client: AsyncClient,
    headers: dict[str, str],
    title: str,
    property_type: str,
    space_label: str,
    vehicle_category: str,
    space_type: str = "COVERED",
    length_m: float = 4.80,
    width_m: float = 2.40,
    height_m: float = 2.10,
    has_ev: bool = False,
    tariff_paise: int = 5000,
    doc_type: str = "PROPERTY_TAX_RECEIPT",
) -> str:
    # 1. Create Property
    prop_resp = await client.post(
        "/api/v1/properties",
        json={
            "title": title,
            "property_type": property_type,
            "address_line": "123 Pairwise Avenue",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    # 2. Add Space
    await client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": space_label,
            "space_type": space_type,
            "vehicle_category": vehicle_category,
            "length_meters": length_m,
            "width_meters": width_m,
            "height_clearance_meters": height_m,
            "has_ev_charging": has_ev,
            "base_hourly_rate_paise": tariff_paise,
        },
        headers=headers,
    )

    # 3. Add Schedule (Monday 08:00 - 18:00)
    await client.post(
        f"/api/v1/properties/{prop_id}/operating-hours",
        json={"day_of_week": 1, "start_time": "08:00:00", "end_time": "18:00:00"},
        headers=headers,
    )

    # 4. Presign & Verify Document
    p_resp = await client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": doc_type,
            "file_name": "auth.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=headers,
    )
    doc_id = p_resp.json()["document_id"]
    await client.post(
        f"/api/v1/properties/{prop_id}/documents/{doc_id}/verify", headers=headers
    )

    # 5. Submit for Review
    await client.post(f"/api/v1/properties/{prop_id}/submit-review", headers=headers)
    return prop_id


# =============================================================================
# Combinations 1 - 12: Property Type × Vehicle × EV × Review Decisions
# =============================================================================


@pytest.mark.asyncio
async def test_c01_residential_driveway_sedan_no_ev_approved(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C01: RESIDENTIAL_DRIVEWAY + SEDAN + No EV + Standard Hours -> Ops APPROVE."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_id = await setup_property_for_review(
        e2e_client,
        owner_headers,
        "Res Sedan Driveway",
        "RESIDENTIAL_DRIVEWAY",
        "SED-01",
        "SEDAN",
        length_m=4.80,
        width_m=2.40,
        height_m=2.10,
        has_ev=False,
    )
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec), "version": 1},
        headers=ops_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_c02_residential_driveway_suv_ev_approved(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C02: RESIDENTIAL_DRIVEWAY + SUV + With EV Charging -> Ops APPROVE."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_id = await setup_property_for_review(
        e2e_client,
        owner_headers,
        "Res EV SUV Driveway",
        "RESIDENTIAL_DRIVEWAY",
        "EV-SUV-01",
        "SUV",
        length_m=5.20,
        width_m=2.50,
        height_m=2.20,
        has_ev=True,
    )
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec), "version": 1},
        headers=ops_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_c03_residential_driveway_two_wheeler_rejected_doc(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C03: RESIDENTIAL_DRIVEWAY + TWO_WHEELER -> Ops REJECT (DOC_ILLEGIBLE)."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_id = await setup_property_for_review(
        e2e_client,
        owner_headers,
        "Res Bike Spot",
        "RESIDENTIAL_DRIVEWAY",
        "BIKE-01",
        "TWO_WHEELER",
        length_m=2.20,
        width_m=1.00,
        height_m=2.00,
        has_ev=False,
    )
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "Illegible receipt",
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_c04_apartment_society_hatchback_no_ev_approved(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C04: APARTMENT_SOCIETY + HATCHBACK + No EV -> Ops APPROVE."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_id = await setup_property_for_review(
        e2e_client,
        owner_headers,
        "Apt Compact Spot",
        "APARTMENT_SOCIETY",
        "CP-01",
        "HATCHBACK",
        length_m=4.20,
        width_m=2.20,
        height_m=2.10,
        has_ev=False,
        doc_type="SOCIETY_NOC",
    )
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec), "version": 1},
        headers=ops_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_c05_apartment_society_suv_ev_approved(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C05: APARTMENT_SOCIETY + SUV + With EV -> Ops APPROVE."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_id = await setup_property_for_review(
        e2e_client,
        owner_headers,
        "Apt EV SUV Spot",
        "APARTMENT_SOCIETY",
        "APT-EV-1",
        "SUV",
        length_m=5.00,
        width_m=2.50,
        height_m=2.20,
        has_ev=True,
        doc_type="SOCIETY_NOC",
    )
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec), "version": 1},
        headers=ops_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_c06_apartment_society_two_wheeler_rejected_noc(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C06: APARTMENT_SOCIETY + TWO_WHEELER -> Ops REJECT (SOCIETY_NOC_MISSING)."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_id = await setup_property_for_review(
        e2e_client,
        owner_headers,
        "Apt Bike Spot",
        "APARTMENT_SOCIETY",
        "AB-01",
        "TWO_WHEELER",
        length_m=2.20,
        width_m=1.00,
        height_m=2.00,
        has_ev=False,
    )
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "SOCIETY_NOC_MISSING",
            "reviewer_notes": "Secretary signature missing",
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_c07_commercial_building_sedan_ev_approved(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C07: COMMERCIAL_BUILDING + SEDAN + With EV -> Ops APPROVE."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_id = await setup_property_for_review(
        e2e_client,
        owner_headers,
        "Commercial EV Sedan",
        "COMMERCIAL_BUILDING",
        "COM-SED-1",
        "SEDAN",
        length_m=4.80,
        width_m=2.40,
        height_m=2.10,
        has_ev=True,
        doc_type="LEASE_AGREEMENT",
    )
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec), "version": 1},
        headers=ops_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_c08_commercial_building_suv_no_ev_approved(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C08: COMMERCIAL_BUILDING + SUV + No EV -> Ops APPROVE."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_id = await setup_property_for_review(
        e2e_client,
        owner_headers,
        "Commercial SUV",
        "COMMERCIAL_BUILDING",
        "COM-SUV-1",
        "SUV",
        length_m=5.20,
        width_m=2.50,
        height_m=2.20,
        has_ev=False,
        doc_type="LEASE_AGREEMENT",
    )
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec), "version": 1},
        headers=ops_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_c09_commercial_building_hatchback_rejected_deed(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C09: COMMERCIAL_BUILDING + HATCHBACK -> Ops REJECT (INVALID_OWNERSHIP_PROOF)."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_id = await setup_property_for_review(
        e2e_client,
        owner_headers,
        "Commercial Compact",
        "COMMERCIAL_BUILDING",
        "COM-CP-1",
        "HATCHBACK",
        length_m=4.20,
        width_m=2.20,
        height_m=2.10,
        has_ev=False,
    )
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "INVALID_OWNERSHIP_PROOF",
            "reviewer_notes": "Commercial lease expired",
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_c10_open_plot_suv_no_ev_approved(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C10: OPEN_PLOT + SUV + No EV -> Ops APPROVE."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_id = await setup_property_for_review(
        e2e_client,
        owner_headers,
        "Open Plot SUV Lot",
        "OPEN_PLOT",
        "PLOT-SUV-1",
        "SUV",
        length_m=5.50,
        width_m=2.60,
        height_m=2.50,
        has_ev=False,
        doc_type="SALE_DEED",
    )
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec), "version": 1},
        headers=ops_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_c11_open_plot_ev_two_wheeler_approved(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C11: OPEN_PLOT + EV_TWO_WHEELER + With EV -> Ops APPROVE."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_id = await setup_property_for_review(
        e2e_client,
        owner_headers,
        "Open Plot EV Bikes",
        "OPEN_PLOT",
        "PLOT-EVB-1",
        "EV_TWO_WHEELER",
        length_m=2.40,
        width_m=1.20,
        height_m=2.00,
        has_ev=True,
        doc_type="SALE_DEED",
    )
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec), "version": 1},
        headers=ops_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_c12_open_plot_sedan_rejected_doc(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C12: OPEN_PLOT + SEDAN -> Ops REJECT (DOC_ILLEGIBLE)."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_id = await setup_property_for_review(
        e2e_client,
        owner_headers,
        "Open Plot Sedan Lot",
        "OPEN_PLOT",
        "PLOT-SED-1",
        "SEDAN",
        length_m=4.80,
        width_m=2.40,
        height_m=2.10,
        has_ev=False,
        doc_type="SALE_DEED",
    )
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "Deed pages missing",
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"


# =============================================================================
# Combinations 13 - 20: Cross-Feature Pairing & Vehicle-Space Compatibility
# =============================================================================


@pytest.mark.asyncio
async def test_c13_pair_ev_four_wheeler_on_ev_bay_compatibility():
    """C13: EV 4-Wheeler evaluated on bay with EV charging enabled -> Compatible."""
    vehicle = VehicleDimensions(
        length_mm=4600, width_mm=1850, height_mm=1600, is_ev=True
    )
    space = SpaceDimensions(
        length_mm=5000, width_mm=2300, height_mm=2000, is_ev_charging=True
    )
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is True


@pytest.mark.asyncio
async def test_c14_pair_ev_four_wheeler_on_non_ev_bay_fails():
    """C14: EV 4-Wheeler evaluated on bay WITHOUT EV charging -> Incompatible (EV requirement failed)."""
    vehicle = VehicleDimensions(
        length_mm=4600, width_mm=1850, height_mm=1600, is_ev=True
    )
    space = SpaceDimensions(
        length_mm=5000, width_mm=2300, height_mm=2000, is_ev_charging=False
    )
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is False
    assert any(
        "requires dedicated charging" in r.lower() for r in res.rejection_reasons
    )


@pytest.mark.asyncio
async def test_c15_pair_ev_two_wheeler_on_ev_bike_bay_compatibility():
    """C15: EV Two-Wheeler evaluated on EV Bike Bay -> Compatible."""
    vehicle = VehicleDimensions(
        length_mm=1900, width_mm=750, height_mm=1150, is_ev=True
    )
    space = SpaceDimensions(
        length_mm=2300, width_mm=1200, height_mm=1800, is_ev_charging=True
    )
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is True


@pytest.mark.asyncio
async def test_c16_pair_hatchback_on_sedan_bay_compatibility():
    """C16: Smaller Hatchback parking in a larger Sedan Bay -> Compatible (ample clearance)."""
    hatchback = VehicleDimensions(
        length_mm=3800, width_mm=1700, height_mm=1500, is_ev=False
    )
    sedan_bay = SpaceDimensions(
        length_mm=4900, width_mm=2300, height_mm=2000, is_ev_charging=False
    )
    res = CompatibilityService.evaluate_compatibility(hatchback, sedan_bay)
    assert res.is_compatible is True
    assert res.length_clearance_mm >= 300
    assert res.width_clearance_mm >= 400


@pytest.mark.asyncio
async def test_c17_pair_suv_on_hatchback_bay_incompatible():
    """C17: Large SUV parking in a Compact Hatchback Bay -> Incompatible (clearances deficient)."""
    suv = VehicleDimensions(length_mm=4850, width_mm=1950, height_mm=1750, is_ev=False)
    compact_bay = SpaceDimensions(
        length_mm=4100, width_mm=2100, height_mm=1800, is_ev_charging=False
    )
    res = CompatibilityService.evaluate_compatibility(suv, compact_bay)
    assert res.is_compatible is False
    assert res.length_clearance_mm < 300


@pytest.mark.asyncio
async def test_c18_pair_commercial_building_multi_bay_mixed_types(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C18: COMMERCIAL_BUILDING with 3 diverse bays (Bike, Sedan, EV SUV) approved by Ops."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Mixed Fleet Commercial",
            "property_type": "COMMERCIAL_BUILDING",
            "address_line": "Outer Ring Road",
            "city": "Bengaluru",
            "postal_code": "560103",
            "latitude": 12.9350,
            "longitude": 77.6800,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    # Bay 1: Bike
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "MIX-BIKE",
            "space_type": "OPEN",
            "vehicle_category": "TWO_WHEELER",
            "length_meters": 2.20,
            "width_meters": 1.00,
            "height_clearance_meters": 2.00,
            "base_hourly_rate_paise": 2000,
        },
        headers=owner_headers,
    )
    # Bay 2: Sedan
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "MIX-SEDAN",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 6000,
        },
        headers=owner_headers,
    )
    # Bay 3: EV SUV
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "MIX-EVSUV",
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

    approve_resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec), "version": 1},
        headers=ops_headers,
    )
    assert approve_resp.status_code == 200


@pytest.mark.asyncio
async def test_c19_pair_apartment_society_rejection_resubmission_approval(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """C19: Full lifecycle: Apartment Society rejected for missing NOC -> owner uploads NOC -> resubmits -> approved."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Cycle Society",
            "property_type": "APARTMENT_SOCIETY",
            "address_line": "Kanakapura Road",
            "city": "Bengaluru",
            "postal_code": "560062",
            "latitude": 12.8800,
            "longitude": 77.5500,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "CY-1",
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

    # 1. Reject
    await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "SOCIETY_NOC_MISSING",
            "reviewer_notes": "Please attach NOC.",
        },
        headers=ops_headers,
    )

    # 2. Upload NOC
    p2 = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "SOCIETY_NOC",
            "file_name": "noc.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 2000,
        },
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/{p2.json()['document_id']}/verify",
        headers=owner_headers,
    )

    # 3. Resubmit
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/submit-review", headers=owner_headers
    )

    # 4. Approve with version 2
    approve_resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec), "version": 2},
        headers=ops_headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_c20_pair_open_plot_weekend_schedule_with_blackout(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
):
    """C20: OPEN_PLOT configured with weekend schedule (Sat-Sun) paired with a weekday maintenance blackout."""
    _, owner_headers = owner_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Weekend Open Plot",
            "property_type": "OPEN_PLOT",
            "address_line": "Hennur Road",
            "city": "Bengaluru",
            "postal_code": "560043",
            "latitude": 13.0400,
            "longitude": 77.6500,
        },
        headers=owner_headers,
    )
    prop_id = prop_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "WK-1",
            "space_type": "OPEN",
            "vehicle_category": "SUV",
            "length_meters": 5.20,
            "width_meters": 2.50,
            "height_clearance_meters": 2.20,
            "base_hourly_rate_paise": 6000,
        },
        headers=owner_headers,
    )

    # Saturday (6) and Sunday (0)
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/operating-hours",
        json={"day_of_week": 6, "start_time": "07:00:00", "end_time": "22:00:00"},
        headers=owner_headers,
    )
    await e2e_client.post(
        f"/api/v1/properties/{prop_id}/operating-hours",
        json={"day_of_week": 0, "start_time": "07:00:00", "end_time": "22:00:00"},
        headers=owner_headers,
    )

    # Weekday blackout
    bo_resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/blackouts",
        json={
            "start_time": "2026-12-08T00:00:00Z",
            "end_time": "2026-12-11T23:59:59Z",
            "reason": "Weekday ground leveling",
        },
        headers=owner_headers,
    )
    assert bo_resp.status_code in (200, 201)
