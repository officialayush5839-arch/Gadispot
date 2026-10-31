# SmartPark Exchange — Open-Source Integrations & Technology Evaluation

> **Document Version:** 1.0.0  
> **Last Updated:** 2026-10-31  
> **Status:** Approved Architecture Reference  
> **Authors:** Principal Software Architect, Backend Architect, Mobile Architect, Payment Specialist  

---

## 1. Executive Summary & Core Integration Strategy

SmartPark Exchange is built on the engineering principle of **pragmatic reuse**: leveraging active, battle-tested open-source libraries and official vendor SDKs for commodity capabilities (OTP verification, payment orchestration, barcode rendering, QR scanning, push messaging), while reserving custom engineering for core competitive differentiators (Multi-Source Availability Intelligence, Guaranteed Parking Recovery Protocol, unified ledger, and double-booking exclusion constraints).

### Mandatory Rules
1. **Never trust frontend verification:** Client-side SDK callbacks (e.g., Razorpay Flutter success, Firebase client verification) are strictly presentation hints. Canonical business state transitions require cryptographically verified server-side proofs (HMAC-SHA256 signature verification or Firebase Admin ID token validation).
2. **Provider abstraction:** All third-party providers must sit behind decoupled adapter interfaces. Domain logic must never directly import vendor SDKs.
3. **Transparent total cost of ownership (TCO):** An open-source license (`MIT`, `Apache-2.0`) does not make an external service free. Telecom SMS, payment MDR, route transfer fees, and BaaS quotas must be explicitly budgeted.

---

## 2. Comprehensive Open-Source Repository Audit

| Feature Domain | Target Repository & Package | Verified License | Maintenance & Last Release | Integration Layer | External Service Dependency | Cost Model | Security & Compliance Considerations | Architectural Decision | Technical Justification |
|---|---|---|---|---|---|---|---|---|---|
| **Driver/Owner Mobile Phone Auth** | `firebase/flutterfire` (`firebase_auth`) | BSD-3-Clause | Actively maintained by Invertase & Google; `v6.x+` (stable) | Flutter Mobile Client SDK | Google Cloud / Firebase Authentication & Telecom SMS Gateway | Free tier: 10,000 phone verifications/month. Overage: ~$0.01 to $0.06/verification depending on country/SMS gateway. | SafetyNet/Play Integrity on Android; APNs background notifications on iOS. Requires backend verification via Firebase Admin. | **ADOPT (P0 MVP)** | Standard across mobile development. Handles SMS auto-retrieval, reCAPTCHA fallback, and native device integrity out of the box. |
| **Backend Identity Verification** | `firebase-admin-python` (`firebase-admin`) | Apache-2.0 | Actively maintained by Google; `v6.5+` | FastAPI Backend Core | Google Firebase Project Service Account | Included in Firebase Project (Free tier covers Admin token verification) | Service account private key must be loaded via secure environment variable; checks cryptographic signature, expiration (`exp`), audience (`aud`), and issuer (`iss`). | **ADOPT (P0 MVP)** | Authoritative backend validation of Firebase ID tokens. Exchanges Firebase JWT for internal scoped SmartPark session tokens. |
| **Privileged Staff 2FA / TOTP** | `pyauth/pyotp` | MIT License | Actively maintained; `v2.10.0` (June 2026) | FastAPI Backend (Admin/Ops only) | None (Self-hosted RFC 6238/4226) | 100% Free / Open Source | Standard RFC 6238 TOTP. Requires secure database encryption for TOTP base32 secret keys. | **ADOPT (P1 Internal Ops)** | Zero external operational cost. Eliminates SMS costs for internal operations staff and administrators. Not intended for customer SMS OTP. |
| **Alternative Messaging OTP Gateway** | `Luckyyaduvanshiofficial/wotp` | AGPL-3.0 | Low activity; community project | External Sidecar Service (FastAPI + PocketBase) | WhatsApp Cloud API (Meta) or Telegram Bot API | Meta WhatsApp Conversation charges (~₹0.40 - ₹0.80 per authentication conversation in India) | AGPL-3.0 copyleft risk if integrated into proprietary codebase. Requires maintaining separate Docker container, PocketBase, and Meta business app verification. | **REJECT for MVP** | High legal licensing risk (AGPL-3.0). Operational burden of maintaining PocketBase and Meta WhatsApp Cloud API credentials for MVP is unjustified when Firebase provides a unified flow. |
| **Primary Payment Gateway (Mobile)** | `razorpay/razorpay-flutter` (`razorpay_flutter`) | MIT License | Actively maintained by Razorpay; `v1.4.5` (mid-2026) | Flutter Mobile Client SDK | Razorpay India Merchant Account | 2% + 18% GST MDR on UPI/Cards (0% MDR promotional tier up to ₹5L GMV) | Enforces UPI Intent via native app switching. Client callbacks treated as untrusted; triggers backend status check or awaits webhook. | **ADOPT (P0 MVP)** | Market leader in India. Superior UPI Intent support on Android and iOS. Native app-switch handling for PhonePe, GPay, Paytm, BHIM. |
| **Primary Payment Gateway (Backend)** | `razorpay/razorpay-python` (`razorpay`) | MIT License | Actively maintained; `v2.0.1` | FastAPI Backend Integration Module | Razorpay REST APIs | Included with Razorpay merchant account | SDK is synchronous (`requests`); must be executed within `asyncio.get_event_loop().run_in_executor` to prevent blocking the FastAPI event loop. Validates HMAC-SHA256 signatures. | **ADOPT (P0 MVP)** | Production-proven SDK for order creation, refund initiation, and webhook signature verification (`verify_webhook_signature`). |
| **Marketplace Split Payouts** | Razorpay Route API | Proprietary REST API | Active enterprise capability | FastAPI Backend Integration Module | Razorpay Route Merchant Account (Linked Accounts API) | Standard PG fee + Route transfer fee (~0.25% + GST per transfer) | Subject to RBI Payment Aggregator guidelines. Requires ₹40L+ domestic turnover for full automated Route capability. | **ADOPT (Architecture Ready) / MANUAL FALLBACK (Day 1)** | Programmatically splits driver payment between SmartPark platform commission and owner net payout. If startup turnover threshold (<₹40L) delays Route activation, fallback to batch payout via bank IMPS/NEFT with identical ledger schema. |
| **Alternative Payment Provider** | `cashfree/flutter-cashfree-pg-sdk` & `cashfree-pg-sdk-python` | MIT / Apache-2.0 | Actively maintained; Python `v6.0.1`, Flutter `v2.5.0+53` | Mobile & Backend Adapter | Cashfree Payments India Merchant Account | ~1.95% + GST; promotional zero platform fee up to ₹20L GMV | Auto-generated OpenAPI Python SDK requires `pydantic >= 2.11.7`. Low community visibility on Flutter repo (frequent dSYM iOS issues). | **EVALUATE AS SECONDARY (P1 Fallback)** | Robust payout reputation ("Cashfree Payouts"), but Flutter SDK has significantly smaller community footprint and higher iOS integration complexity. Retained as secondary provider behind adapter. |
| **Booking Access QR Generation** | `theyakka/qr.flutter` (`qr_flutter`) | BSD-3-Clause | Actively maintained; `v4.1.0` | Flutter Mobile Client UI | None (Client-side rendering) | 100% Free / Open Source | Renders opaque, high-entropy cryptographic token (`HMAC-SHA256` or UUIDv4 reference). Never encodes PII, vehicle number, or raw payment IDs into the QR. | **ADOPT (P0 MVP)** | Vector and raster rendering of QR codes with embedded branding/styling. Fast, zero-dependency, full null safety. |
| **Guard QR Code Scanning** | `juliansteenbakker/mobile_scanner` (`mobile_scanner`) | MIT License | High activity; `v5.x / v6.x` | Flutter Guard Scanning Screen | Device Camera Hardware | 100% Free / Open Source | Native MLKit on Android and AVFoundation on iOS. Rapid barcode decoding with torch and camera switching controls. | **ADOPT (P0 MVP)** | Far superior to deprecated `qr_code_scanner`. Native platform performance, minimal battery drain, robust autofocus, and active maintenance. |
| **Deprecated Scanner Candidate** | `juliuscanute/qr_code_scanner` | Apache-2.0 | Unmaintained; deprecated since 2022 | Flutter | Camera | Free | Known Android 13+ camera permission crashes; broken camera lifecycle management. | **REJECT** | Officially deprecated in favor of `mobile_scanner`. |
| **Push Notifications (Mobile)** | `firebase/flutterfire` (`firebase_messaging`) | BSD-3-Clause | Actively maintained by Google/Invertase | Flutter Mobile Client | Firebase Cloud Messaging (FCM) / Apple APNs | Free tier: Unlimited notifications | Device APNs/FCM push tokens registered on login, invalidated on logout. Background/foreground handling. | **ADOPT (P0 MVP)** | Cross-platform standard for real-time booking alerts, hold expiration warnings, and entry/exit updates. |
| **Push Notifications (Backend)** | `firebase-admin-python` (`firebase-admin.messaging`) | Apache-2.0 | Actively maintained by Google | FastAPI Notification Worker | FCM HTTP v1 API | Free tier: Unlimited notifications | Uses OAuth2 service credentials. Supports multicast messages, notification payload data, and priority headers (`high`). | **ADOPT (P0 MVP)** | Reliable push dispatch directly from async FastAPI workers without external commercial notification SaaS. |
| **PostgreSQL Driver & ORM** | `asyncpg` + `SQLAlchemy 2.0` | Apache-2.0 / MIT | Highly active; industry standard | FastAPI Data Layer | Managed PostgreSQL 15+ | 100% Free / Open Source | Native support for PostgreSQL `tstzrange`, `GiST` index, and `EXCLUDE USING gist` for transactional double-booking prevention. | **ADOPT (P0 MVP)** | Maximum performance async PostgreSQL binary driver combined with typed SQLAlchemy 2.0 declarative models. |
| **Cache & Distributed Locks** | `redis-py` (asyncio) | MIT License | Actively maintained; `v5.0+` | FastAPI Cache & State Layer | Managed Redis 7.0+ | 100% Free / Open Source | Atomic key management (`SET NX EX`) for 5-minute temporary booking holds; token bucket rate-limiting algorithms. | **ADOPT (P0 MVP)** | High-throughput sub-millisecond state management for non-durable locks and session counters. |

---

## 3. Modular Provider Adapter Architecture

To prevent vendor lock-in and allow seamless switching or multi-gateway fallback, SmartPark enforces strict repository and service decoupling.

```
smartpark_backend/
├── app/
│   ├── core/                    # Security, config, exceptions
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic v2 schemas
│   ├── api/                     # FastAPI route controllers
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── bookings.py
│   │   │   ├── payments.py
│   │   │   └── webhooks.py
│   └── integrations/            # Pluggable Provider Adapters
│       ├── authentication/
│       │   ├── base.py          # AbstractBaseAuthVerifier
│       │   └── firebase_auth.py # FirebaseAuthVerifier (Admin SDK)
│       ├── payments/
│       │   ├── base.py          # AbstractPaymentGateway
│       │   ├── razorpay_provider.py # RazorpayAdapter
│       │   └── cashfree_provider.py # CashfreeAdapter (Fallback)
│       ├── payouts/
│       │   ├── base.py          # AbstractPayoutEngine
│       │   ├── razorpay_route.py    # RouteAdapter
│       │   └── manual_batch_payout.py # DirectBankTransferAdapter
│       ├── notifications/
│       │   ├── base.py          # AbstractNotificationDispatcher
│       │   └── fcm_provider.py  # FCMDispatcher
│       └── qr/
│           ├── token_service.py # High-entropy HMAC token generator
│           └── qr_validator.py  # State and temporal validator
```

### Python Adapter Interface Example: AbstractPaymentGateway
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class PaymentOrderRequest(BaseModel):
    booking_id: str
    amount_in_paise: int
    currency: str = "INR"
    customer_phone: str
    notes: Dict[str, str]

class PaymentOrderResponse(BaseModel):
    gateway_order_id: str
    amount: int
    currency: str
    checkout_payload: Dict[str, Any]

class WebhookVerificationResult(BaseModel):
    is_valid: bool
    event_type: str
    gateway_payment_id: str
    gateway_order_id: str
    amount_paid: int
    raw_payload: Dict[str, Any]

class AbstractPaymentGateway(ABC):
    @abstractmethod
    async def create_order(self, request: PaymentOrderRequest) -> PaymentOrderResponse:
        """Creates an order at the payment aggregator."""
        pass

    @abstractmethod
    async def verify_webhook_signature(
        self, raw_body: bytes, signature_header: str
    ) -> WebhookVerificationResult:
        """Authoritatively verifies incoming webhook payload."""
        pass

    @abstractmethod
    async def initiate_refund(
        self, gateway_payment_id: str, amount_in_paise: int, reason: str
    ) -> Dict[str, Any]:
        """Initiates full or partial refund to the customer."""
        pass
```

---

## 4. Total Cost of Ownership (TCO) & Operational Transparency

The following matrix documents the real-world operational costs of each external service dependency. None of these dependencies are "free" merely because the client SDK is open source.

| Integration Component | Open Source Software Cost | External Infrastructure / Service Cost | Minimum Merchant Commitment & Onboarding | Billing Unit / Metering Basis |
|---|---|---|---|---|
| **Firebase Phone Auth** | ₹0 (BSD-3-Clause) | Free Tier: 10,000 verifications/month. Thereafter: ~$0.015 per SMS verification in India (~₹1.25/SMS). | Google Cloud Account + Billing Enablement (Credit Card / Cloud Billing). Play Integrity configuration required. | Per successful phone verification. |
| **Razorpay Payment Gateway** | ₹0 (MIT) | 2.0% + 18% GST on all card, netbanking, and UPI transactions (Net: 2.36%). Promotional 0% fee up to ₹5,00,000 GMV for early startups. | Business KYC: PAN, GSTIN / Udyam Certificate, Bank Statement, CKYC verification. | Per captured payment transaction. |
| **Razorpay Route (Marketplace)** | ₹0 (API access) | ~0.25% + 18% GST per transfer split to linked bank account (*subject to final commercial contract*). | Requires ₹40L+ annual turnover (verified via GSTR-3B) per RBI PA guidelines. Vendor linked account penny-drop verification: ₹1 + GST per check. | Per automated transfer and per account validation. |
| **Firebase Cloud Messaging (FCM)** | ₹0 (BSD-3-Clause) | Free / 100% Google subsidized. No API charges for push message delivery. | Google Service Account with FCM v1 API enabled. APNs Certificate ($99/year Apple Developer fee). | Unlimited notifications. |
| **Managed PostgreSQL (AWS RDS / Supabase / Neon)** | ₹0 (PostgreSQL Core) | ~$25 - $70/month for development/staging (2 vCPU, 4GB RAM, 50GB SSD). | AWS / Cloud Provider Account. | Hourly compute + provisioned IOPS storage. |
| **Managed Redis (ElastiCache / Upstash / Redis Cloud)** | ₹0 (Redis Core) | ~$15 - $40/month (1GB - 2GB RAM cache cluster with persistence). | Cloud Provider Account. | Memory allocation + bandwidth transfer. |
| **Map Rendering & Geocoding** | `flutter_map` / OpenStreetMap (Free) OR Google Maps Flutter | Google Maps: $200 free monthly credit; $7 per 1,000 map loads thereafter. OSM/Mapbox: Free tier with quota. | Google Cloud Platform API Key / Mapbox Token with restricted package name / bundle ID. | Per Dynamic Map Load / Geocoding API call. |

---

## 5. Security & Verification Requirements for Integrations

### 5.1 OTP Authentication Security
1. **No Plaintext OTP Storage:** SmartPark does not generate, receive, or store SMS OTP strings in the database. Firebase Authentication verifies the OTP directly on the handset, returning a cryptographically signed Firebase ID token.
2. **Backend Token Verification:** FastAPI receives the Bearer ID token and validates:
   - Token signature using Google's public x509 certificates.
   - Expiration timestamp (`exp > now()`).
   - Audience (`aud == FIREBASE_PROJECT_ID`).
   - Issuer (`iss == https://securetoken.google.com/<FIREBASE_PROJECT_ID>`).
   - Phone number extraction (`decoded_token["phone_number"]`).
3. **Internal Session Token:** Once verified, the backend issues an internal scoped SmartPark JWT (access token: 60-minute TTL; refresh token: 30-day TTL in secure HTTP-only storage/mobile secure storage).

### 5.2 Payment Webhook Verification Protocol
1. **Raw Body Integrity:** Webhook validation must use the unprocessed raw request body bytes (`request.body()`). Deserializing to JSON and re-serializing alters whitespace and invalidates the HMAC signature.
2. **Secret Separation:** The Razorpay Webhook Secret (`RAZORPAY_WEBHOOK_SECRET`) must be completely distinct from the API Key Secret (`RAZORPAY_KEY_SECRET`).
3. **Idempotency Protection:** Every incoming webhook delivery includes `x-razorpay-event-id`. The backend checks Redis with a 24-hour TTL:
   ```python
   is_new = await redis_client.set(f"webhook:event:{event_id}", "processed", nx=True, ex=86400)
   if not is_new:
       return Response(status_code=200, content="Duplicate event ignored")
   ```
4. **Amount & Currency Check:** The verified captured amount in paise must match `booking.amount_paise` exactly.

### 5.3 Two QR Code Systems Separation
Under no circumstances may the **Payment Dynamic QR** and the **Parking Access QR** share keys, schemas, or verification endpoints.

```
+---------------------------------------------------------------------------------------------------+
|                                  TWO DISTINCT QR CODE SYSTEMS                                     |
+------------------------------------+--------------------------------------------------------------+
| 1. Dynamic Payment QR              | 2. Parking Access QR                                         |
+------------------------------------+--------------------------------------------------------------+
| • Origin: Razorpay API             | • Origin: SmartPark Backend Engine                          |
| • Consumer: Driver UPI Mobile App  | • Consumer: SmartPark Guard App                              |
| • Encodes: UPI Virtual Address/URL | • Encodes: High-entropy opaque cryptosecure token UUIDv4     |
| • Purpose: Transfer funds via UPI  | • Purpose: Physical gate validation & session initiation     |
| • Lifetime: Exactly 5 minutes (TTL)| • Lifetime: Booking start - 15 min through booking end time  |
| • Security: NPCI BharatQR standard | • Security: One-time burn upon entry, replay protection      |
+------------------------------------+--------------------------------------------------------------+
```

---

## 6. Implementation Summary & Dependencies for Mobile/Backend

### Mobile `pubspec.yaml` Specifications
```yaml
dependencies:
  flutter:
    sdk: flutter
  
  # Authentication & Cloud Messaging
  firebase_core: ^3.10.0
  firebase_auth: ^5.4.0
  firebase_messaging: ^15.2.0

  # Payment Orchestration
  razorpay_flutter: ^1.3.7

  # Access QR Generation & Barcode Scanning
  qr_flutter: ^4.1.0
  mobile_scanner: ^6.0.4

  # Networking & Secure Storage
  dio: ^5.7.0
  flutter_secure_storage: ^9.2.2
```

### Backend `pyproject.toml` / `requirements.txt` Specifications
```toml
[dependencies]
fastapi = ">=0.115.0"
uvicorn = {extras = ["standard"], version = ">=0.32.0"}
pydantic = ">=2.9.2"
pydantic-settings = ">=2.6.0"
sqlalchemy = ">=2.0.36"
asyncpg = ">=0.30.0"
redis = ">=5.2.0"
firebase-admin = ">=6.6.0"
razorpay = ">=2.0.1"
pyotp = ">=2.10.0"
cryptography = ">=43.0.3"
```
