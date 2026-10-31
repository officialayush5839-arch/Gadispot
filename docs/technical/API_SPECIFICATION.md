# SmartPark Exchange — Comprehensive REST API Specification (V2.2)

> **Document Version:** 2.2.0  
> **Date:** October 31, 2026  
> **API Standard:** OpenAPI 3.1 / RESTful JSON  
> **Backend Framework:** Python FastAPI  
> **Base URL:** `https://api.smartpark.in/api/v1`  
> **Status:** Authoritative Engineering Design (Targeted Revision V2.2)  

---

## 1. Global API Standards & Conventions

### 1.1 Authentication & Authorization
- **Mechanism:** HTTP Bearer Authentication with JSON Web Tokens (JWT).
- **Header:** `Authorization: Bearer <smartpark_access_token>`.
- **Token Claims:** Scoped `sub` (User UUID), `role` (`DRIVER`, `OWNER`, `GUARD`, `OPERATIONS`, `ADMIN`), `exp` (60-minute TTL).
- **Object-Level Authorization (IDOR Defense):** Endpoints derive user identity strictly from authenticated token claims; query parameters cannot override caller identity.

### 1.2 Idempotency Protocol
- All mutating endpoints (`POST`, `PUT`, `DELETE`) creating financial holds, reservations, payments, or gate scan entries **strictly require** the `Idempotency-Key` header (UUIDv4).
- Idempotency is persisted in the PostgreSQL database table (`payment_webhook_events` / `space_reservations`) and accelerated in Redis with a 24-hour TTL.
- If a request is received with an existing key, the identical cached JSON response and status code are returned without re-executing side effects.

### 1.3 Standard Error Response Schema (RFC 7807)
All error responses adhere to the RFC 7807 Problem Details JSON format:

```json
{
  "type": "https://api.smartpark.in/errors/EXCLUSION_CONFLICT",
  "title": "Time Slot Already Reserved",
  "status": 409,
  "detail": "The requested parking bay is already held or booked for the specified time interval.",
  "instance": "/api/v1/bookings/hold",
  "code": "SLOT_INTERVAL_CONFLICT",
  "timestamp": "2026-10-31T10:14:22Z"
}
```

---

## 2. API Endpoint Inventory by Domain

### 2.1 Authentication & Profile (`/auth`, `/users`)

#### `POST /auth/session`
- **Purpose:** Exchange verified Firebase ID token for internal SmartPark JWT.
- **Role:** Public (No auth required).
- **Request Body:** `{"firebase_id_token": "eyJhbGciOiJSUzI1NiIs..."}`
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "refresh_token": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
      "phone_number": "+919876543210",
      "full_name": "Rohan Sharma",
      "active_role": "DRIVER",
      "available_roles": ["DRIVER", "OWNER"]
    }
  }
  ```

#### `POST /auth/switch-role`
- **Purpose:** Switch active role between Driver and Owner without re-authenticating.
- **Role:** Authenticated (Must possess target role).
- **Request Body:** `{"target_role": "OWNER"}`
- **Response (200 OK):** Returns new scoped JWT with `role: "OWNER"`.

---

### 2.2 Discovery & Search (`/spaces`)

#### `POST /spaces/search`
- **Purpose:** Spatial PostGIS and MSAI temporal search for verified, bookable bays.
- **Role:** Public / Driver.
- **Request Body:**
  ```json
  {
    "latitude": 12.9352,
    "longitude": 77.6245,
    "radius_meters": 3000,
    "start_time": "2026-10-31T14:00:00+05:30",
    "end_time": "2026-10-31T16:00:00+05:30",
    "vehicle_category": "SEDAN",
    "features": {
      "covered": false,
      "ev_charging": false
    }
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "total_found": 3,
    "spaces": [
      {
        "space_id": "c3d9a1f2-7b8c-4e5a-9f1d-2b3c4d5e6f7a",
        "property_id": "b1a2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
        "property_name": "Koramangala Green Villa",
        "bay_identifier": "Slot 1",
        "distance_meters": 420,
        "hourly_rate_inr": 40.00,
        "total_estimate_inr": 91.80,
        "space_type": "COVERED",
        "is_ev_charging": false,
        "photos": [
          "https://cdn.smartpark.in/photos/prop_1_entrance.jpg",
          "https://cdn.smartpark.in/photos/prop_1_bay.jpg"
        ],
        "operating_hours": "08:00 - 20:00",
        "amenities": ["CCTV", "GATED_ENTRY", "GUARD_ON_DUTY"]
      }
    ]
  }
  ```

---

### 2.3 Booking & Hold Engine (`/bookings`)

#### `POST /bookings/hold`
- **Purpose:** Atomically reserve a parking space for strictly 480 seconds (8 minutes) during checkout.
- **Role:** Driver.
- **Headers:** `Idempotency-Key: <UUID>`
- **Request Body:**
  ```json
  {
    "parking_space_id": "c3d9a1f2-7b8c-4e5a-9f1d-2b3c4d5e6f7a",
    "vehicle_id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a",
    "start_time": "2026-10-31T14:00:00+05:30",
    "end_time": "2026-10-31T16:00:00+05:30"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "reservation_id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
    "booking_reference": "SPX-982143",
    "status": "ACTIVE_HOLD",
    "hold_expires_at": "2026-10-31T13:48:00+05:30",
    "pricing_breakdown": {
      "base_parking_inr": 80.00,
      "convenience_fee_inr": 10.00,
      "gst_inr": 1.80,
      "total_payable_inr": 91.80,
      "amount_paise": 9180
    },
    "payment_gateway": {
      "provider": "RAZORPAY",
      "order_id": "order_MNb7654321",
      "key_id": "rzp_test_12345678"
    }
  }
  ```
- **Error Responses:**
  - `409 Conflict`: Slot overlaps with existing hold or booking (`SLOT_INTERVAL_CONFLICT`).
  - `400 Bad Request`: Time window outside property schedule or duration < 30 minutes (`POL-DUR-01`).

---

### 2.4 Payment Webhooks & Status (`/webhooks`, `/payments`)

#### `POST /webhooks/razorpay`
- **Purpose:** Authoritative ingestion of asynchronous payment aggregator webhooks with durable database idempotency.
- **Role:** Public (Raw HMAC SHA-256 Verified).
- **Headers:** `X-Razorpay-Signature: <HMAC_HEX>`, `X-Razorpay-Event-Id: <EVENT_ID>`.
- **Request Body:** Raw Razorpay Webhook JSON payload (`payment.captured`, `payment.failed`, `refund.processed`).
- **Response (200 OK):** `{"status": "PROCESSED"}`.
- **Error Responses:**
  - `400 Bad Request`: Invalid HMAC signature.
  - `200 OK`: Duplicate event ID already recorded in `payment_webhook_events` (Idempotent dismiss).

#### `GET /payments/verify-status/{order_id}`
- **Purpose:** Polling fallback when webhook is delayed by network congestion.
- **Role:** Driver.
- **Response (200 OK):**
  ```json
  {
    "order_id": "order_MNb7654321",
    "reservation_id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
    "status": "CONFIRMED",
    "access_qr_issued": true
  }
  ```

---

### 2.5 Parking Access & Gate Operations (`/access`)

#### `GET /access/credentials/{reservation_id}`
- **Purpose:** Retrieve active one-time access QR token for confirmed reservation.
- **Role:** Driver (Must own reservation).
- **Response (200 OK):**
  ```json
  {
    "reservation_id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
    "entry_token": "spx_ent_98f4e2b17a6c0d8e4f1a2b3c4d5e6f7a",
    "exit_token": "spx_ext_1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
    "entry_valid_from": "2026-10-31T13:45:00+05:30",
    "entry_valid_until": "2026-10-31T14:30:00+05:30",
    "exit_valid_until": "2026-10-31T16:15:00+05:30",
    "status": "ISSUED",
    "property": {
      "name": "Koramangala Green Villa",
      "address": "42, 4th Cross, 5th Block, Koramangala",
      "bay_label": "Slot 1"
    }
  }
  ```

#### `POST /access/validate-scan`
- **Purpose:** Security guard camera scan validation of driver's presented Entry QR code.
- **Role:** Guard (Must be assigned to target property).
- **Headers:** `Idempotency-Key: <UUID>`
- **Request Body:**
  ```json
  {
    "opaque_token": "spx_ent_98f4e2b17a6c0d8e4f1a2b3c4d5e6f7a",
    "property_id": "b1a2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "guard_device_timestamp": "2026-10-31T13:52:10+05:30"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "action": "ADMIT_VEHICLE",
    "reservation_id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
    "booking_reference": "SPX-982143",
    "bay_label": "Slot 1",
    "vehicle_plate": "KA-01-AB-1234",
    "driver_name": "Rohan Sharma",
    "valid_until": "16:00 (Grace to 16:15)",
    "session_status": "ACTIVE_SESSION"
  }
  ```

#### `POST /access/validate-exit`
- **Purpose:** Security guard scan validation of driver's Exit QR code and overstay assessment.
- **Role:** Guard.
- **Request Body:** `{"opaque_token": "spx_ext_1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"}`
- **Response (200 OK):**
  ```json
  {
    "action": "DEPARTURE_CLEARED",
    "session_status": "COMPLETED",
    "overstay_minutes": 0,
    "overstay_penalty_inr": 0.00
  }
  ```

#### `POST /access/reconcile-offline-admissions`
- **Purpose:** Synchronize offline manual admissions recorded in underground basements during network outages.
- **Role:** Guard / Attendant.
- **Request Body:**
  ```json
  {
    "admissions": [
      {
        "vehicle_plate": "KA-01-AB-1234",
        "admitted_at": "2026-10-31T14:05:00+05:30",
        "driver_phone_last4": "3210",
        "reason_code": "DEEP_BASEMENT_OUTAGE",
        "photo_s3_key": "photos/offline/audit_9812.jpg",
        "event_signature": "sha256_hash_here",
        "device_fingerprint": "guard_dev_001"
      }
    ]
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "reconciled_count": 1,
    "conflicts": []
  }
  ```
