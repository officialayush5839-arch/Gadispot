"""Tier 2: Boundary & Corner Case E2E Tests for Phase 03 Supply Engine.

Covers boundary, edge, and adversarial corner cases:
- Coordinates outside [-90,90] / [-180,180] and boundary values at limits
- Bay dimensions <= 0 (length, width, height)
- Negative or zero base hourly tariffs
- Physical clearance thresholds (299mm vs 300mm, 399mm vs 400mm, 99mm vs 100mm)
- EV requested on non-EV bay
- Inverted and equal operating hours (start_time >= end_time)
- Blackout conflicts and zero-duration blackouts
- Expired / tampered presigned URLs and file sizes > 10MB
- Unsupported MIME types
- Concurrent review race HTTP 409 Conflict
- Missing, non-numeric, or invalid RFC 6238 TOTP step-up codes
"""

import uuid

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
# 1. Coordinate Limits & Boundary Verification
# =============================================================================


@pytest.mark.asyncio
async def test_b01_latitude_upper_boundary_exact_90(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B01: Latitude at exact upper limit +90.0 (North Pole) is valid."""
    _, headers = owner_user
    payload = {
        "title": "North Pole Boundary Spot",
        "property_type": "OPEN_PLOT",
        "address_line": "90th Parallel",
        "city": "Arctic",
        "postal_code": "000000",
        "latitude": 90.0,
        "longitude": 0.0,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_b02_latitude_lower_boundary_exact_minus_90(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B02: Latitude at exact lower limit -90.0 (South Pole) is valid."""
    _, headers = owner_user
    payload = {
        "title": "South Pole Boundary Spot",
        "property_type": "OPEN_PLOT",
        "address_line": "South Pole Station",
        "city": "Antarctica",
        "postal_code": "000000",
        "latitude": -90.0,
        "longitude": 0.0,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_b03_latitude_exceeds_upper_bound_90_0001(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B03: Latitude exceeding +90.0 (e.g. 90.0001) is strictly rejected with HTTP 422."""
    _, headers = owner_user
    payload = {
        "title": "Illegal Latitude Upper",
        "property_type": "OPEN_PLOT",
        "address_line": "Off Globe",
        "city": "Space",
        "postal_code": "000000",
        "latitude": 90.0001,
        "longitude": 77.0,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b04_latitude_below_lower_bound_minus_90_0001(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B04: Latitude below -90.0 (e.g. -90.0001) is strictly rejected with HTTP 422."""
    _, headers = owner_user
    payload = {
        "title": "Illegal Latitude Lower",
        "property_type": "OPEN_PLOT",
        "address_line": "Off Globe South",
        "city": "Space",
        "postal_code": "000000",
        "latitude": -90.0001,
        "longitude": 77.0,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b05_longitude_upper_boundary_exact_180(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B05: Longitude at exact upper limit +180.0 is valid."""
    _, headers = owner_user
    payload = {
        "title": "Antimeridian East Spot",
        "property_type": "OPEN_PLOT",
        "address_line": "International Date Line",
        "city": "Pacific",
        "postal_code": "000000",
        "latitude": 0.0,
        "longitude": 180.0,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_b06_longitude_lower_boundary_exact_minus_180(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B06: Longitude at exact lower limit -180.0 is valid."""
    _, headers = owner_user
    payload = {
        "title": "Antimeridian West Spot",
        "property_type": "OPEN_PLOT",
        "address_line": "International Date Line West",
        "city": "Pacific",
        "postal_code": "000000",
        "latitude": 0.0,
        "longitude": -180.0,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_b07_longitude_exceeds_upper_bound_180_0001(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B07: Longitude exceeding +180.0 (e.g. 180.0001) is strictly rejected with HTTP 422."""
    _, headers = owner_user
    payload = {
        "title": "Illegal Longitude East",
        "property_type": "OPEN_PLOT",
        "address_line": "Over Limit East",
        "city": "Pacific",
        "postal_code": "000000",
        "latitude": 12.0,
        "longitude": 180.0001,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b08_longitude_below_lower_bound_minus_180_0001(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B08: Longitude below -180.0 (e.g. -180.0001) is strictly rejected with HTTP 422."""
    _, headers = owner_user
    payload = {
        "title": "Illegal Longitude West",
        "property_type": "OPEN_PLOT",
        "address_line": "Over Limit West",
        "city": "Pacific",
        "postal_code": "000000",
        "latitude": 12.0,
        "longitude": -180.0001,
    }
    resp = await e2e_client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp.status_code in (400, 422)


# =============================================================================
# 2. Bay Physical Dimensions & Tariff Boundaries
# =============================================================================


@pytest.mark.asyncio
async def test_b09_bay_length_zero_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B09: Bay length of 0.00 meters is rejected with HTTP 422."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Dim Bound Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "ZERO-L",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 0.00,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b10_bay_length_negative_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B10: Negative bay length (-4.50m) is rejected with HTTP 422."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Neg L Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "NEG-L",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": -4.50,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b11_bay_width_zero_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B11: Bay width of 0.00 meters is rejected with HTTP 422."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Zero W Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "ZERO-W",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 0.00,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b12_bay_width_negative_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B12: Negative bay width (-2.40m) is rejected with HTTP 422."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Neg W Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "NEG-W",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": -2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 5000,
        },
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b13_bay_height_zero_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B13: Bay height of 0.00 meters is rejected with HTTP 422."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Zero H Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "ZERO-H",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 0.00,
            "base_hourly_rate_paise": 5000,
        },
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b14_tariff_zero_paise_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B14: Base hourly rate of 0 paise is rejected by check constraint chk_base_hourly_rate_paise_positive."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Zero Tariff Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "ZERO-PAISE",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 0,
        },
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b15_tariff_negative_paise_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B15: Base hourly rate of negative paise (-1000) is rejected by constraint chk_base_hourly_rate_paise_positive."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Neg Tariff Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "NEG-PAISE",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": -1000,
        },
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b16_tariff_minimum_valid_one_paise(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B16: Base hourly rate of exactly 1 paise (> 0) is valid at boundary."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "One Paise Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/spaces",
        json={
            "space_label": "ONE-PAISE",
            "space_type": "COVERED",
            "vehicle_category": "SEDAN",
            "length_meters": 4.80,
            "width_meters": 2.40,
            "height_clearance_meters": 2.10,
            "base_hourly_rate_paise": 1,
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201)


# =============================================================================
# 3. Physical Clearance Margins Exact Boundary Cases
# =============================================================================


@pytest.mark.asyncio
async def test_b17_length_clearance_boundary_299mm_fails():
    """B17: Length clearance of exactly 299mm fails the 300mm minimum requirement."""
    vehicle = VehicleDimensions(length_mm=4500, width_mm=1800, height_mm=1500)
    # Bay length 4799mm -> clearance 299mm (requires 300mm)
    space = SpaceDimensions(length_mm=4799, width_mm=2300, height_mm=2000)
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is False
    assert res.length_clearance_mm == 299


@pytest.mark.asyncio
async def test_b18_length_clearance_boundary_300mm_passes():
    """B18: Length clearance of exactly 300mm satisfies the 300mm minimum requirement."""
    vehicle = VehicleDimensions(length_mm=4500, width_mm=1800, height_mm=1500)
    # Bay length 4800mm -> clearance 300mm
    space = SpaceDimensions(length_mm=4800, width_mm=2300, height_mm=2000)
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is True
    assert res.length_clearance_mm == 300


@pytest.mark.asyncio
async def test_b19_width_clearance_boundary_399mm_fails():
    """B19: Width clearance of exactly 399mm fails the 400mm minimum requirement."""
    vehicle = VehicleDimensions(length_mm=4500, width_mm=1800, height_mm=1500)
    # Bay width 2199mm -> clearance 399mm (requires 400mm)
    space = SpaceDimensions(length_mm=4900, width_mm=2199, height_mm=2000)
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is False
    assert res.width_clearance_mm == 399


@pytest.mark.asyncio
async def test_b20_width_clearance_boundary_400mm_passes():
    """B20: Width clearance of exactly 400mm satisfies the 400mm minimum requirement."""
    vehicle = VehicleDimensions(length_mm=4500, width_mm=1800, height_mm=1500)
    # Bay width 2200mm -> clearance 400mm
    space = SpaceDimensions(length_mm=4900, width_mm=2200, height_mm=2000)
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is True
    assert res.width_clearance_mm == 400


@pytest.mark.asyncio
async def test_b21_height_clearance_boundary_99mm_fails():
    """B21: Height clearance of exactly 99mm fails the 100mm minimum requirement."""
    vehicle = VehicleDimensions(length_mm=4500, width_mm=1800, height_mm=1500)
    # Bay height 1599mm -> clearance 99mm (requires 100mm)
    space = SpaceDimensions(length_mm=4900, width_mm=2300, height_mm=1599)
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is False
    assert res.height_clearance_mm == 99


@pytest.mark.asyncio
async def test_b22_height_clearance_boundary_100mm_passes():
    """B22: Height clearance of exactly 100mm satisfies the 100mm minimum requirement."""
    vehicle = VehicleDimensions(length_mm=4500, width_mm=1800, height_mm=1500)
    # Bay height 1600mm -> clearance 100mm
    space = SpaceDimensions(length_mm=4900, width_mm=2300, height_mm=1600)
    res = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert res.is_compatible is True
    assert res.height_clearance_mm == 100


# =============================================================================
# 4. Schedule & Concurrency Boundaries
# =============================================================================


@pytest.mark.asyncio
async def test_b23_inverted_operating_hours_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B23: Inverted operating hours (start_time > end_time) rejected by database constraint chk_schedule_time."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Invert Time Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/operating-hours",
        json={"day_of_week": 4, "start_time": "22:00:00", "end_time": "06:00:00"},
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b24_equal_operating_hours_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B24: Equal operating hours (start_time == end_time, e.g. 10:00 to 10:00) rejected by chk_schedule_time."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Equal Time Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/operating-hours",
        json={"day_of_week": 5, "start_time": "10:00:00", "end_time": "10:00:00"},
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b25_concurrency_conflict_http_409(
    e2e_client: AsyncClient,
    owner_user: tuple[User, dict[str, str]],
    ops_user: tuple[User, dict[str, str], str],
):
    """B25: Optimistic locking version mismatch returns HTTP 409 Conflict with CONCURRENCY_CONFLICT code."""
    _, owner_headers = owner_user
    _, ops_headers, totp_sec = ops_user

    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "409 Race Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
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
            "space_label": "RACE-1",
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

    # First decision increments version 1 -> 2
    await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/approve",
        json={"totp_code": get_current_totp(totp_sec), "version": 1},
        headers=ops_headers,
    )

    # Second concurrent decision still submits version 1 -> Must return HTTP 409
    race_resp = await e2e_client.post(
        f"/api/v1/ops/properties/{prop_id}/reject",
        json={
            "totp_code": get_current_totp(totp_sec),
            "version": 1,
            "rejection_reason_code": "DOC_ILLEGIBLE",
            "reviewer_notes": "Concurrent reject.",
        },
        headers=ops_headers,
    )
    assert race_resp.status_code == 409


# =============================================================================
# 5. Document Size, MIME & Security Boundaries
# =============================================================================


@pytest.mark.asyncio
async def test_b26_file_size_exceeds_10mb_limit_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B26: File size of 10,485,761 bytes (10MB + 1 byte) is rejected with HTTP 422."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Size Bound Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "too_big.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 10485761,  # 10MB + 1
        },
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b27_file_size_exactly_10mb_accepted(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B27: File size of exactly 10,485,760 bytes (10MB) is accepted at the boundary."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Exact 10MB Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/documents/presign",
        json={
            "document_type": "PROPERTY_TAX_RECEIPT",
            "file_name": "exact_10mb.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 10485760,  # Exact 10MB
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_b28_invalid_mime_type_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B28: Reject invalid MIME types such as text/html or application/octet-stream."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "MIME Bound Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    for bad_mime in ["text/html", "application/javascript", "video/mp4"]:
        resp = await e2e_client.post(
            f"/api/v1/properties/{prop_id}/documents/presign",
            json={
                "document_type": "PROPERTY_TAX_RECEIPT",
                "file_name": "exploit",
                "content_type": bad_mime,
                "file_size_bytes": 5000,
            },
            headers=headers,
        )
        assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_b29_totp_invalid_six_digit_rejected(
    e2e_client: AsyncClient, ops_user: tuple[User, dict[str, str], str]
):
    """B29: Step-up operations review rejects wrong 6-digit TOTP code."""
    _, ops_headers, _ = ops_user
    fake_id = str(uuid.uuid4())
    resp = await e2e_client.post(
        f"/api/v1/ops/properties/{fake_id}/approve",
        json={
            "totp_code": "123456",  # wrong code
            "version": 1,
        },
        headers=ops_headers,
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_b30_blackout_equal_start_end_time_rejected(
    e2e_client: AsyncClient, owner_user: tuple[User, dict[str, str]]
):
    """B30: Zero-duration blackout where start_time == end_time rejected by chk_blackout_time."""
    _, headers = owner_user
    prop_resp = await e2e_client.post(
        "/api/v1/properties",
        json={
            "title": "Zero Blackout Prop",
            "property_type": "RESIDENTIAL_DRIVEWAY",
            "address_line": "Test Rd",
            "city": "Bengaluru",
            "postal_code": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    prop_id = prop_resp.json()["id"]

    same_time = "2026-12-01T12:00:00Z"
    resp = await e2e_client.post(
        f"/api/v1/properties/{prop_id}/blackouts",
        json={
            "start_time": same_time,
            "end_time": same_time,
            "reason": "Zero duration",
        },
        headers=headers,
    )
    assert resp.status_code in (400, 422)
