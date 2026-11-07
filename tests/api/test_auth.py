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
async def test_api_totp_setup_and_verify_endpoints():
    """Verify /api/v1/auth/2fa/setup and /2fa/verify endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        setup_resp = await client.post("/api/v1/auth/2fa/setup")
        assert setup_resp.status_code == 200
        setup_data = setup_resp.json()
        assert "secret" in setup_data
        assert setup_data["qr_code_base64"].startswith("data:image/png;base64,")

        secret = setup_data["secret"]
        code = pyotp.TOTP(secret).now()

        verify_resp = await client.post(
            "/api/v1/auth/2fa/verify",
            json={"secret": secret, "code": code},
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["valid"] is True

        bad_verify_resp = await client.post(
            "/api/v1/auth/2fa/verify",
            json={"secret": secret, "code": "999999"},
        )
        assert bad_verify_resp.status_code == 200
        assert bad_verify_resp.json()["valid"] is False
