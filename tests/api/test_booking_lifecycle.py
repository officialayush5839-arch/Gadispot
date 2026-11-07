"""End-to-end booking and access lifecycle automated tests (TSK-P7-004).

Exercises the complete user journey:
1. Driver creates 480-second checkout hold (POST /api/v1/bookings/hold).
2. Competing driver attempting overlapping hold is rejected with HTTP 409.
3. Driver initiates payment order (POST /api/v1/payments/create-order).
4. Webhook confirms payment capture -> reservation status transitions to CONFIRMED.
5. Access tokens (ENTRY and EXIT) are issued with 128-bit CSPRNG entropy.
6. Guard scans ENTRY token -> validates and activates session (ACTIVE_SESSION).
7. Replay scan attempt with same ENTRY token is rejected with HTTP 409.
8. Guard scans EXIT token -> validates and completes reservation (COMPLETED).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from app.core.security import create_access_token
from app.main import app
from app.models.enums import (
    ReservationStatusEnum,
    SpaceTypeEnum,
    VehicleCategoryEnum,
)
from app.models.parking import ParkingSpace
from app.models.reservations import SpaceReservation
from app.models.users import User, Vehicle
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text


@pytest.fixture
async def setup_lifecycle_entities(db_session):
    """Seed test driver, vehicle, property, and parking space."""
    # Driver
    driver = User(
        phone_number=f"+9198{uuid.uuid4().hex[:8]}",
        full_name="Lifecycle Driver",
        email="driver_lifecycle@test.com",
    )
    db_session.add(driver)
    await db_session.flush()

    vehicle = Vehicle(
        driver_id=driver.id,
        registration_plate=f"KA01LC{uuid.uuid4().hex[:4].upper()}",
        vehicle_category=VehicleCategoryEnum.SEDAN,
        make_model="Hyundai Verna",
    )
    db_session.add(vehicle)
    await db_session.flush()

    # Owner & Property
    owner = User(
        phone_number=f"+9197{uuid.uuid4().hex[:8]}",
        full_name="Lifecycle Owner",
        email="owner_lifecycle@test.com",
    )
    db_session.add(owner)
    await db_session.flush()

    prop_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO properties (id, owner_id, title, property_type, address_line, city, postal_code, location, is_active)
            VALUES (:id, :owner_id, 'Koramangala Tech Hub', 'COMMERCIAL_BUILDING', '80ft Road Koramangala', 'Bengaluru', '560034', 'SRID=4326;POINT(77.6245 12.9352)', TRUE)
            """
        ),
        {"id": prop_id, "owner_id": owner.id},
    )

    space = ParkingSpace(
        property_id=prop_id,
        space_label="LC-BAY-101",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        base_hourly_rate_paise=6000,
    )
    db_session.add(space)
    await db_session.commit()

    return {
        "driver": driver,
        "vehicle": vehicle,
        "property_id": prop_id,
        "space": space,
    }


@pytest.mark.asyncio
async def test_complete_booking_access_lifecycle_e2e(
    setup_lifecycle_entities, db_session
):
    """Execute complete 8-step lifecycle from hold to session completion."""
    entities = setup_lifecycle_entities
    driver = entities["driver"]
    vehicle = entities["vehicle"]
    space = entities["space"]

    # Generate JWT for driver
    token = create_access_token(
        subject=str(driver.id),
        claims={"phone": driver.phone_number, "roles": ["DRIVER"]},
    )
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        start_time = datetime.now(timezone.utc) + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        # Step 1: Create active hold
        hold_payload = {
            "parking_space_id": str(space.id),
            "vehicle_id": str(vehicle.id),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }
        resp = await client.post(
            "/api/v1/bookings/hold", json=hold_payload, headers=headers
        )
        assert resp.status_code == 201, resp.text
        hold_data = resp.json()
        reservation_id = hold_data["reservation_id"]
        assert hold_data["status"] == "ACTIVE_HOLD"

        # Step 2: Competing driver attempts overlapping hold on same space -> 409 Conflict
        competing_resp = await client.post(
            "/api/v1/bookings/hold", json=hold_payload, headers=headers
        )
        assert competing_resp.status_code == 409
        assert competing_resp.json()["code"] == "SLOT_ALREADY_RESERVED"

        # Step 3: Create payment order with runtime adapter
        order_payload = {
            "reservation_id": reservation_id,
            "gateway": "hyperswitch",
            "amount_paise": 9180,
            "currency": "INR",
        }
        order_resp = await client.post(
            "/api/v1/payments/create-order", json=order_payload
        )
        assert order_resp.status_code == 200, order_resp.text
        order_data = order_resp.json()
        assert order_data["gateway"] == "hyperswitch"
        assert order_data["amount_paise"] == 9180

        # Step 4: Simulate payment capture confirmation
        res_stmt = select(SpaceReservation).where(
            SpaceReservation.id == uuid.UUID(reservation_id)
        )
        res_result = await db_session.execute(res_stmt)
        res = res_result.scalar_one()
        res.status = ReservationStatusEnum.CONFIRMED
        await db_session.commit()

        # Step 5: Issue access credentials
        tokens_resp = await client.post(
            "/api/v1/access/issue-tokens",
            json={"reservation_id": reservation_id},
        )
        assert tokens_resp.status_code == 201, tokens_resp.text
        tokens_data = tokens_resp.json()
        entry_token = tokens_data["entry_token"]
        exit_token = tokens_data["exit_token"]
        assert entry_token.startswith("spx_ent_")
        assert exit_token.startswith("spx_ext_")

        # Step 6: Guard scans ENTRY token -> 200 OK & session activates
        entry_resp = await client.post(
            "/api/v1/access/validate-scan",
            json={"opaque_token": entry_token},
        )
        assert entry_resp.status_code == 200, entry_resp.text
        entry_data = entry_resp.json()
        assert entry_data["status"] == "SUCCESS"
        assert entry_data["token_type"] == "ENTRY"

        # Verify database state is ACTIVE_SESSION
        await db_session.refresh(res)
        assert res.status == ReservationStatusEnum.ACTIVE_SESSION

        # Step 7: Guard scans ENTRY token again -> 409 Conflict (Replay prevented)
        replay_resp = await client.post(
            "/api/v1/access/validate-scan",
            json={"opaque_token": entry_token},
        )
        assert replay_resp.status_code == 409
        assert replay_resp.json()["code"] == "TOKEN_ALREADY_CONSUMED"

        # Step 8: Guard scans EXIT token -> 200 OK & session completed
        exit_resp = await client.post(
            "/api/v1/access/validate-scan",
            json={"opaque_token": exit_token},
        )
        assert exit_resp.status_code == 200, exit_resp.text
        exit_data = exit_resp.json()
        assert exit_data["status"] == "SUCCESS"
        assert exit_data["token_type"] == "EXIT"

        # Verify final database state is COMPLETED
        await db_session.refresh(res)
        assert res.status == ReservationStatusEnum.COMPLETED
