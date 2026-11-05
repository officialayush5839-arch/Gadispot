"""Pydantic schemas for booking holds and reservations."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class CreateHoldRequest(BaseModel):
    parking_space_id: uuid.UUID
    vehicle_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    idempotency_key: str | None = None


class HoldResponse(BaseModel):
    reservation_id: uuid.UUID
    booking_reference: str
    parking_space_id: uuid.UUID
    driver_id: uuid.UUID
    status: str
    hold_expires_at: datetime


class ReservationDetailResponse(BaseModel):
    reservation_id: uuid.UUID
    booking_reference: str
    parking_space_id: uuid.UUID
    driver_id: uuid.UUID
    status: str
    payment_order_id: str | None = None
    hold_expires_at: datetime | None = None
    created_at: datetime
