"""Automated tests for Phase 5 authentication, JWT session management, and PyOTP 2FA."""

import uuid

import pyotp
import pytest
from app.core.exceptions import UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
)
from app.main import app
from app.services.auth_service import (
    generate_totp_secret,
    get_totp_provisioning_uri,
    verify_totp_code,
)
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_access_and_refresh_token_lifecycle():
    """Verify standard creation, claim verification, and token type checking."""
    sub = str(uuid.uuid4())
    claims = {"phone_number": "+919876543210", "roles": ["DRIVER"]}

    access_token = create_access_token(subject=sub, claims=claims)
    refresh_token = create_refresh_token(subject=sub, claims=claims)

    decoded_access = decode_token(access_token)
    assert decoded_access["sub"] == sub
    assert decoded_access["type"] == "access"
    assert decoded_access["roles"] == ["DRIVER"]
    verify_token_type(decoded_access, "access")

    decoded_refresh = decode_token(refresh_token)
    assert decoded_refresh["sub"] == sub
    assert decoded_refresh["type"] == "refresh"
    verify_token_type(decoded_refresh, "refresh")

    with pytest.raises(UnauthorizedException) as exc_info:
        verify_token_type(decoded_access, "refresh")
    assert exc_info.value.code == "INVALID_TOKEN_TYPE"


@pytest.mark.asyncio
async def test_forged_token_signature_rejected():
    """Verify that tampering with token payload or signature is detected."""
    sub = str(uuid.uuid4())
    token = create_access_token(subject=sub)
    tampered_token = token[:-5] + "XXXXX"

    with pytest.raises(UnauthorizedException) as exc_info:
        decode_token(tampered_token)
    assert exc_info.value.code == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_api_auth_session_exchange(db_session):
    """Verify POST /api/v1/auth/session exchanges verified token for scoped JWT."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Valid test token
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-driver:{phone}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["phone_number"] == phone
        assert "DRIVER" in data["user"]["roles"]

        # 2. Refresh token flow
        refresh_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": data["refresh_token"]},
        )
        assert refresh_resp.status_code == 200
        refresh_data = refresh_resp.json()
        assert "access_token" in refresh_data
        assert refresh_data["user"]["phone_number"] == phone


@pytest.mark.asyncio
async def test_api_auth_forged_token_rejected():
    """Verify POST /api/v1/auth/session rejects forged/invalid tokens."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": "completely-invalid-malformed-token-string"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["code"] == "FIREBASE_TOKEN_INVALID"


@pytest.mark.asyncio
async def test_pyotp_totp_2fa_flow():
    """Verify RFC 6238 TOTP generation, URI generation, and code verification."""
    secret = generate_totp_secret()
    assert len(secret) == 32
    uri = get_totp_provisioning_uri(secret, "operations@gadispot.in")
    assert "otpauth://totp/" in uri
    assert "Gadispot%20Operations" in uri or "Gadispot" in uri

    # Generate current code using pyotp
    totp = pyotp.TOTP(secret)
    current_code = totp.now()

    assert verify_totp_code(secret, current_code) is True
    assert verify_totp_code(secret, "000000") is False
    assert verify_totp_code(secret, "123") is False


@pytest.mark.asyncio
async def test_api_totp_setup_and_verify_endpoints(db_session):
    """Verify /api/v1/auth/2fa/setup and /2fa/verify endpoints with strict account binding."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated setup must be rejected
        unauth_resp = await client.post("/api/v1/auth/2fa/setup")
        assert unauth_resp.status_code == 401

        # 2. Authenticate principal
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        auth_resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-totp:{phone}"},
        )
        assert auth_resp.status_code == 200
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Authenticated setup succeeds and returns provisioning QR code
        setup_resp = await client.post("/api/v1/auth/2fa/setup", headers=headers)
        assert setup_resp.status_code == 200
        setup_data = setup_resp.json()
        assert "secret" in setup_data
        assert setup_data["qr_code_base64"].startswith("data:image/png;base64,")

        secret = setup_data["secret"]
        code = pyotp.TOTP(secret).now()

        # 4. Valid verification against account-persisted secret succeeds
        verify_resp = await client.post(
            "/api/v1/auth/2fa/verify",
            headers=headers,
            json={"code": code},
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["valid"] is True

        # 5. Bad code returns valid=False
        bad_verify_resp = await client.post(
            "/api/v1/auth/2fa/verify",
            headers=headers,
            json={"code": "000000"},
        )
        assert bad_verify_resp.status_code == 200
        assert bad_verify_resp.json()["valid"] is False


@pytest.mark.asyncio
async def test_identity_conflict_on_phone_with_different_firebase_uid(db_session):
    """Verify that an existing account's phone cannot be taken over by presenting a conflicting Firebase UID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        # 1. Register User with initial Firebase token
        resp1 = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-userA:{phone}"},
        )
        assert resp1.status_code == 200

        # 2. Attempt to present the same phone number with a conflicting Firebase identity
        # In test mode, prefixing test-token-userB changes the generated UID
        from unittest.mock import patch

        with patch("app.services.auth_service.verify_firebase_token") as mock_verify:
            mock_verify.return_value = {
                "uid": "malicious-conflicting-uid-12345",
                "phone_number": phone,
                "email": None,
            }
            resp2 = await client.post(
                "/api/v1/auth/session",
                json={"id_token": "some-token"},
            )
            # Must fail closed with 409 Conflict (PHONE_ALREADY_LINKED)
            assert resp2.status_code == 409
            assert resp2.json()["code"] == "PHONE_ALREADY_LINKED"


@pytest.mark.asyncio
async def test_concurrent_refresh_token_rotation_atomic(db_session):
    """Verify that concurrent requests with the same refresh token cannot both succeed."""
    import asyncio

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-race:{phone}"},
        )
        assert resp.status_code == 200
        refresh_token = resp.json()["refresh_token"]

        # Concurrently dispatch 2 refresh requests using the exact same refresh token
        res1, res2 = await asyncio.gather(
            client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}),
            client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}),
            return_exceptions=True,
        )

        status_codes = [r.status_code for r in (res1, res2) if hasattr(r, "status_code")]
        # Exactly one request must succeed (200), and the other must be rejected (401)
        assert 200 in status_codes
        assert 401 in status_codes


@pytest.mark.asyncio
async def test_authoritative_database_revocation_fallback_when_redis_unavailable(db_session):
    """Verify that when Redis is unreachable, revoked session families are rejected via DB fallback."""
    from unittest.mock import AsyncMock, patch

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        auth_resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-fallback:{phone}"},
        )
        assert auth_resp.status_code == 200
        data = auth_resp.json()
        token = data["access_token"]
        refresh_token = data["refresh_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # Verify active token works
        profile_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert profile_resp.status_code == 200

        # Now revoke the session in DB (simulate reuse or explicit termination)
        from app.models.session import UserSession
        from sqlalchemy import update
        from datetime import datetime, timezone

        await db_session.execute(
            update(UserSession)
            .where(UserSession.user_id == uuid.UUID(data["user"]["id"]))
            .values(is_revoked=True, revoked_at=datetime.now(timezone.utc))
        )
        await db_session.commit()

        # Simulate complete Redis outage
        import redis.asyncio as aioredis

        with patch("app.core.dependencies.aioredis.from_url") as mock_redis_factory:
            mock_client = AsyncMock()
            mock_client.get.side_effect = aioredis.ConnectionError("Redis cluster unreachable")
            mock_redis_factory.return_value = mock_client

            # With Redis down, the authoritative DB fallback must catch that the session family is revoked!
            revoked_resp = await client.get("/api/v1/auth/me", headers=headers)
            assert revoked_resp.status_code == 401
            assert revoked_resp.json()["code"] == "TOKEN_REVOKED"
