# Gadispot Open-Source Dependency Register

> **Document Version:** 1.0.0 (Phase 0 Engineering Baseline)  
> **Authoritative Specification:** `PRD-GSP-2026-V2.3.2-VERIFIED`  
> **Audience:** Principal Architects, Security Engineers, Backend Developers, Flutter Developers  
> **Last Updated:** 2026-11-05T11:30:00Z  
> **Compliance Standard:** Zero proprietary vendor lock-in; open-source-first architecture; permissive licenses (Apache-2.0, MIT, BSD-3-Clause).

---

## 1. Executive Summary & Policy

In accordance with Section 5 and Section 6 of `ORIGINAL_REQUEST.md`, Gadispot enforces an **Open-Source-First Architecture**. We prioritize battle-tested, actively maintained open-source libraries and protocols over proprietary, closed-source SDKs wherever appropriate. 

Every external dependency admitted into the Gadispot codebase must undergo rigorous technical scrutiny across six dimensions:
1. **Permissive Licensing:** Exclusively Apache-2.0, MIT, or BSD-3-Clause. AGPL, GPL, or proprietary closed-source licenses are prohibited for core application dependencies.
2. **Active Maintenance:** Regular commits, active issue triage, and updates within the last 90 days.
3. **Security Posture:** Clean vulnerability audit trails on PyPI and pub.dev; no active CVEs.
4. **Architectural Isolation:** Clean abstraction behind ports and adapters (e.g., `PaymentGatewayPort`).
5. **Modern SDK Compatibility:** Compatible with Python 3.11–3.14 and modern Flutter SDKs without legacy Gradle/CocoaPods breakage.
6. **No Fake Bypasses:** Zero client-side proof-of-payment shortcuts or fake verification hacks.

---

## 2. Comprehensive Dependency Register

### 2.1 Payment Infrastructure & Alternatives to Razorpay

| Project Name | Official Repository | License | Latest Release | Maintenance Status | Security Considerations | Purpose in Gadispot | Decision | Engineering Justification |
|---|---|:---:|:---:|:---:|---|---|:---:|---|
| **Hyperswitch** | `https://github.com/juspay/hyperswitch` | **Apache-2.0** | `v0.2.x` (Active) | **Very Active** (Juspay / Linux Foundation) | Written in Rust (memory safe, zero buffer overflows). Self-hosted in container; requires PostgreSQL & Redis. | Universal Payment Orchestration Platform (POP). Dynamic routing and failover across Indian acquirers (Razorpay, Cashfree, PhonePe). | **ADOPT (Phase 5 / Scaling)** | 100% free open-source alternative to proprietary gateways. Eliminates vendor lock-in to Razorpay; switches traffic automatically if a gateway has downtime. |
| **Cashfree Python SDK** | `https://github.com/cashfree/cashfree-pg-sdk-python` | **Apache-2.0** | `v4.3.x` | **Active** (Cashfree Payments) | Uses HTTPS API with app_id / secret_key headers; verified webhooks via signature verification. | Secondary standby payment gateway adapter (`CashfreePaymentAdapter`) and automated bank payouts. | **ADOPT (P0 Standby)** | Promotional 0% gateway fee up to ₹20L GMV. Industry-leading IMPS payout APIs for owner weekly settlements. |
| **Cashfree Flutter SDK** | `https://github.com/cashfree/flutter-cashfree-pg-sdk` | **MIT** | `v2.1.x` | **Active** (Cashfree Payments) | Native Android/iOS bridges. Requires up-to-date Gradle/CocoaPods configurations. | Mobile checkout bridge for Cashfree payments. | **ADOPT (P0 Standby)** | Native UPI intent launch in Flutter client for secondary gateway flow. |
| **NPCI UPI Intent & Dynamic QR** | NPCI UPI Linking Specification | **Open Public Standard** | UPI 2.0 | **Active Standard** (NPCI) | Public standard. **CRITICAL RISK:** Client deep link callback has NO server-side proof of settlement without Bank Webhook API. | Dynamic UPI QR encoding (`upi://pay?pa=...`) and native app intent switcher (`url_launcher`). | **ADOPT (QR URI Spec Only)** | 0% transaction fee / 0% MDR on UPI. Used for URI string formatting, but payment confirmation must route through gateway/bank webhooks. |
| **Razorpay Python SDK** | `https://github.com/razorpay/razorpay-python` | **MIT** | `v2.0.1` | **Maintained** (Razorpay) | Synchronous HTTP calls via `requests`. Must be called in `run_in_executor` to avoid blocking FastAPI event loop. | Primary payment gateway adapter (`RazorpayPaymentAdapter`) for MVP checkout and webhooks. | **ADOPT (P0 Primary)** | Broadest UPI app coverage in India; battle-tested webhook signatures. |

### 2.2 QR Generation, Rendering & Scanning Libraries

| Project Name | Official Repository | License | Latest Release | Maintenance Status | Security Considerations | Purpose in Gadispot | Decision | Engineering Justification |
|---|---|:---:|:---:|:---:|---|---|:---:|---|
| **Python `qrcode[pil]`** | `https://github.com/lincolnloop/python-qrcode` | **BSD-3-Clause** | `v8.0` | **Active** | Mature, pure Python image generation with Pillow. Handles SVG/PNG streams in memory. | Backend dynamic UPI payment QR generation and testing utility. | **ADOPT** | Battle-tested, zero vulnerabilities, lightweight generation of NPCI UPI QR payloads. |
| **`qr_flutter`** | `https://github.com/theyakka/qr.flutter` | **BSD-3-Clause** | `v4.1.0` | **Active** | Pure Dart rendering via `CustomPainter`. Zero native bridge vulnerabilities. | Client-side rendering of high-contrast 128-bit CSPRNG entry/exit access passes on mobile screen. | **ADOPT** | Fast vector-based rendering; supports custom error correction (Level M/Q) and center styling. |
| **`mobile_scanner`** | `https://github.com/juliansteenbakker/mobile_scanner` | **MIT** | `v6.0.4` | **Very Active** | Native camera permissions (Android CameraX / iOS AVFoundation); MLKit on-device barcode parsing. | Security guard app QR code camera scanning. | **ADOPT** | High-performance hardware acceleration; active maintenance; completely replaces deprecated `qr_code_scanner`. |

### 2.3 Authentication, Identity & Cryptography

| Project Name | Official Repository | License | Latest Release | Maintenance Status | Security Considerations | Purpose in Gadispot | Decision | Engineering Justification |
|---|---|:---:|:---:|:---:|---|---|:---:|---|
| **Firebase Admin Python SDK** | `https://github.com/firebase/firebase-admin-python` | **Apache-2.0** | `v7.7.0` | **Very Active** (Google) | Verifies RS256 JWT signatures against Google's public x509 certs with local caching. | Backend verification of client-submitted Firebase ID tokens in `POST /api/v1/auth/session`. | **ADOPT** | Industry standard for mobile phone auth verification; ensures zero trust in client phone claims. |
| **PyOTP** | `https://github.com/pyotp/pyotp` | **MIT** | `v2.10.0` | **Active** | Pure Python RFC 6238 TOTP implementation. Secrets must be encrypted at rest in PostgreSQL. | Privileged Operations 2FA for administrative audits and manual payout overrides. | **ADOPT** | Lightweight, zero-dependency RFC 6238 implementation; works seamlessly with Google Authenticator. |
| **Python `secrets` & `cryptography`** | Python Standard Library & `pyca/cryptography` | **PSFL / Apache-2.0** | Python 3.11+ / `v43.x` | **Standard** | CSPRNG OS-level entropy (`/dev/urandom` / Windows `CryptGenRandom`). | Minting 128-bit unguessable opaque parking access tokens (`spx_ent_...` / `spx_ext_...`). | **ADOPT** | Cryptographically unguessable token generation ($< 2^{-128}$ collision probability). |

### 2.4 Backend Core Framework & Database Utilities

| Project Name | Official Repository | License | Latest Release | Maintenance Status | Security Considerations | Purpose in Gadispot | Decision | Engineering Justification |
|---|---|:---:|:---:|:---:|---|---|:---:|---|
| **FastAPI** | `https://github.com/fastapi/fastapi` | **MIT** | `v0.115.0+` | **Very Active** | Async ASGI framework; OpenAPI 3.1 generation; Pydantic 2 request validation. | Core backend application framework for the modular monolith. | **ADOPT** | High concurrency, native async, automatic documentation, and strict typed validation. |
| **SQLAlchemy 2.x** | `https://github.com/sqlalchemy/sqlalchemy` | **MIT** | `v2.0.36` | **Very Active** | Async ORM and Core SQL expression builder; parameterized queries prevent SQL injection. | Declarative domain models and database mapping. | **ADOPT** | Enterprise-grade ORM with native async support and complete PostgreSQL DDL type safety. |
| **Alembic** | `https://github.com/sqlalchemy/alembic` | **MIT** | `v1.13.3` | **Very Active** | Version-controlled DDL migration tool for SQLAlchemy. | Managing database schema revisions, triggers, extensions, and constraints. | **ADOPT** | Eliminates handcoded DDL strings; enables deterministic schema migrations across dev and CI. |
| **asyncpg** | `https://github.com/MagicStack/asyncpg` | **Apache-2.0** | `v0.30.0` | **Active** | Ultra-fast async PostgreSQL binary protocol driver. Requires proper connection pool lifecycle. | High-performance asynchronous database connection pool. | **ADOPT** | Up to 5x faster than psycopg2; native PostgreSQL range and GiST type support. |
| **Pydantic 2.x & Settings** | `https://github.com/pydantic/pydantic` | **MIT** | `v2.9.2` | **Very Active** | Rust-based core (`pydantic-core`); fast type validation; environment variable parsing. | Request/response DTOs and environment-based configuration management. | **ADOPT** | Fail-fast validation on invalid configuration; sub-millisecond serialization. |
| **HTTPX** | `https://github.com/encode/httpx` | **BSD-3-Clause** | `v0.27.2` | **Very Active** | Asynchronous HTTP client with connection pooling and HTTP/2 support. | Outbound webhook dispatch, SMS gateway API calls, and integration test client. | **ADOPT** | Async client prevents blocking the FastAPI event loop during external API calls. |

---

## 3. Version Pin Harmonization: Outdated vs. Modern Pins

The Phase 0 audit revealed that planned pins in legacy documentation (`docs/product/OPEN_SOURCE_INTEGRATIONS.md`) contained obsolete version declarations that cause build failures with modern toolchains. The table below harmonizes and establishes the authoritative pins:

| Subsystem | Package Name | Legacy Outdated Pin | Modern Harmonized Pin | Status / Rationale |
|---|---|:---:|:---:|---|
| **Flutter** | `firebase_core` | `^3.10.0` | **`^5.1.0`** | **UPGRADED:** Legacy pin incompatible with modern Flutter SDKs and Android Gradle Plugin 8+. |
| **Flutter** | `firebase_auth` | `^5.4.0` | **`^7.0.1`** | **UPGRADED:** Requires `firebase_core ^5.x`; fixes Play Integrity device verification bugs. |
| **Flutter** | `firebase_messaging` | `^14.x` | **`^15.2.0`** | **UPGRADED:** Supports latest Android 14+ notification trampoline restrictions. |
| **Flutter** | `dio` | `^5.4.0` | **`^5.7.0`** | **UPGRADED:** Fixes HTTP/2 connection reuse and cancellation tokens. |
| **Flutter** | `flutter_secure_storage`| `^9.0.0` | **`^9.2.2`** | **UPGRADED:** Resolves Android Keystore migration issues on Android 14. |
| **Flutter** | `qr_flutter` | `^4.1.0` | **`^4.1.0`** | **VERIFIED:** Current stable release on pub.dev. |
| **Flutter** | `mobile_scanner` | `^5.x` | **`^6.0.4`** | **UPGRADED:** Stable CameraX lifecycle management and barcode detection. |
| **Python** | `firebase-admin` | `>= 6.6.0` | **`>= 7.7.0`** | **UPGRADED:** PyPI release with updated Google OAuth credentials and Python 3.12/3.13 support. |
| **Python** | `pyotp` | `>= 2.9.0` | **`>= 2.10.0`** | **UPGRADED:** Python 3.12+ datetime deprecation fixes. |
| **Python** | `fastapi` | `^0.109.0` | **`>= 0.115.0`** | **UPGRADED:** Lifespan management and Pydantic 2.9 compatibility. |
| **Python** | `sqlalchemy` | `^2.0.25` | **`>= 2.0.36`** | **UPGRADED:** Fixes asyncpg connection pool leaks under concurrency. |
| **Python** | `alembic` | *(Missing)* | **`>= 1.13.3`** | **ADDED:** Strictly required for version-controlled database migrations. |
| **Python** | `asyncpg` | `>= 0.29.0` | **`>= 0.30.0`** | **UPGRADED:** Improved socket error recovery and Windows loop handling. |
| **Python** | `httpx` | *(Missing)* | **`>= 0.27.2`** | **ADDED:** Strictly required for async external payment calls. |
| **Python** | `qrcode[pil]` | *(Missing)* | **`>= 8.0`** | **ADDED:** Strictly required for dynamic UPI QR generation. |

---

## 4. Evaluation of Open-Source Payment Switch: Hyperswitch by Juspay

### 4.1 Architecture & Positioning in Gadispot
```
+------------------------------------------------------------------------------------+
|                                GADISPOT BACKEND                                    |
|                                                                                    |
|   [ BookingService ] ---> [ PaymentGatewayPort ] (Common Typed Interface)         |
|                                  |                                                 |
|         +------------------------+------------------------+                        |
|         |                        |                        |                        |
|         v                        v                        v                        |
|   [ RazorpayAdapter ]    [ CashfreeAdapter ]    [ HyperswitchAdapter ]             |
|   (P0 Direct Gateway)    (P0 Direct Standby)    (Self-Hosted POP Switch)           |
+---------|------------------------|------------------------|------------------------+
          |                        |                        |
          |                        |                        +---> [ Hyperswitch Engine ]
          |                        |                              (Rust Orchestrator)
          |                        |                                    |
          v                        v                                    +---> Razorpay
   (Razorpay Rail)          (Cashfree Rail)                             +---> Cashfree
                                                                        +---> PhonePe
                                                                        +---> Direct UPI
```

### 4.2 Key Evaluation Findings
1. **License & Cost:** Apache-2.0. 100% free software license with zero per-transaction software fees when self-hosted.
2. **Performance:** Written in Rust; memory safe; sub-millisecond routing latency; highly efficient connection pooling.
3. **Smart Routing & Failover:** Automatically re-routes checkout transactions to a secondary gateway if the primary gateway's success rate drops below 90%, preventing lost revenue during bank or gateway outages.
4. **Unified Webhook Handling:** Ingests webhooks from 50+ payment providers and emits a normalized event payload, drastically simplifying backend reconciliation.
5. **Phase 1 vs Phase 5 Tradeoff:** Hyperswitch requires hosting a dedicated Rust service container, PostgreSQL database, and Redis cache. For Day 1 MVP (Phase 1–4), direct adapter integration with Razorpay + Cashfree fallback provides a lightweight operational footprint. Hyperswitch will be introduced in Phase 5 as the universal payment orchestration switch.

---

## 5. Security & Governance Review

- **Zero Committed Secrets:** All open-source adapters read credentials strictly from environment variables (`settings.RAZORPAY_KEY_ID`, `settings.CASHFREE_APP_ID`, etc.).
- **Raw Webhook Signature Verification:** All payment webhooks verify HMAC-SHA256 signatures against raw request bytes before parsing JSON payloads.
- **Dependency Vulnerability Scanning:** All Python dependencies are scanned via `pip-audit`, and Flutter dependencies via `flutter pub audit` in CI.
