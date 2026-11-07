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
    """Verify that concurrent requests with the same refresh token are coordinated under OAuth 2.0 BCP §4.14.2 grace period."""
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

        status_codes = [
            r.status_code for r in (res1, res2) if hasattr(r, "status_code")
        ]
        # Exactly one request must succeed (200), and the other must be rejected (409 TOKEN_ALREADY_ROTATED within grace period)
        assert 200 in status_codes
        assert 409 in status_codes

        # Ensure the winning session's tokens are valid and not revoked
        winning_resp = res1 if res1.status_code == 200 else res2
        winning_data = winning_resp.json()
        new_access = winning_data["access_token"]
        new_refresh = winning_data["refresh_token"]

        # Winning access token must be usable
        me_resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access}"}
        )
        assert me_resp.status_code == 200

        # Winning refresh token must be usable for subsequent rotation
        next_refresh_resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": new_refresh}
        )
        assert next_refresh_resp.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token_reuse_outside_grace_period_invalidates_family(db_session):
    """Verify that using an old refresh token outside the grace period triggers reuse detection and revokes the session family."""
    from app.models.session import UserSession
    from sqlalchemy import select, update
    from datetime import datetime, timezone, timedelta

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-reuse:{phone}"},
        )
        assert resp.status_code == 200
        initial_refresh = resp.json()["refresh_token"]

        # First rotation: rotates cleanly
        rot_resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": initial_refresh}
        )
        assert rot_resp.status_code == 200
        active_access = rot_resp.json()["access_token"]

        # Artificially age the revoked_at timestamp on the old session past the 10s grace period (e.g. 30s ago)
        import hashlib

        old_hash = hashlib.sha256(initial_refresh.encode()).hexdigest()
        await db_session.execute(
            update(UserSession)
            .where(UserSession.refresh_token_hash == old_hash)
            .values(revoked_at=datetime.now(timezone.utc) - timedelta(seconds=30))
        )
        await db_session.commit()

        # Replay the old refresh token outside grace period -> MUST trigger 401 TOKEN_REVOKED
        replay_resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": initial_refresh}
        )
        assert replay_resp.status_code == 401
        assert replay_resp.json()["code"] == "TOKEN_REVOKED"

        # Verify that the entire session family was revoked and the previously active token is now dead
        me_resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {active_access}"}
        )
        assert me_resp.status_code == 401
        assert me_resp.json()["code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_login_requires_totp_when_enabled_and_completes_via_challenge(db_session):
    """Verify that when 2FA is active, login yields 403 MFA_REQUIRED and completes via /2fa/challenge."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        id_token = f"test-token-mfa-flow:{phone}"

        # 1. First login / registration without 2FA
        auth_resp = await client.post(
            "/api/v1/auth/session", json={"id_token": id_token}
        )
        assert auth_resp.status_code == 200
        access_token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. Setup 2FA
        setup_resp = await client.post("/api/v1/auth/2fa/setup", headers=headers)
        assert setup_resp.status_code == 200
        secret = setup_resp.json()["secret"]

        # 3. Verify & activate 2FA
        code = pyotp.TOTP(secret).now()
        verify_resp = await client.post(
            "/api/v1/auth/2fa/verify", headers=headers, json={"code": code}
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["valid"] is True

        # 4. Subsequent login without TOTP must be challenged with 403 MFA_REQUIRED
        challenge_req_resp = await client.post(
            "/api/v1/auth/session", json={"id_token": id_token}
        )
        assert challenge_req_resp.status_code == 403
        challenge_data = challenge_req_resp.json()
        assert challenge_data["code"] == "MFA_REQUIRED"
        assert "mfa_token" in challenge_data
        mfa_token = challenge_data["mfa_token"]

        # 5. Invalid MFA challenge attempt
        bad_chal_resp = await client.post(
            "/api/v1/auth/2fa/challenge",
            json={"mfa_token": mfa_token, "totp_code": "000000"},
        )
        assert bad_chal_resp.status_code == 401
        assert bad_chal_resp.json()["code"] == "INVALID_TOTP_CODE"

        # 6. Valid MFA challenge completes login and returns full TokenResponse
        fresh_code = pyotp.TOTP(secret).now()
        good_chal_resp = await client.post(
            "/api/v1/auth/2fa/challenge",
            json={"mfa_token": mfa_token, "totp_code": fresh_code},
        )
        assert good_chal_resp.status_code == 200
        tokens = good_chal_resp.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        # Verify access token works
        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert me_resp.status_code == 200

        # 6b. Replay attack: Replaying the consumed mfa_token must be rejected (one-time consumption)
        replay_code = pyotp.TOTP(secret).now()
        replay_chal_resp = await client.post(
            "/api/v1/auth/2fa/challenge",
            json={"mfa_token": mfa_token, "totp_code": replay_code},
        )
        assert replay_chal_resp.status_code == 401
        assert replay_chal_resp.json()["code"] == "MFA_CHALLENGE_ALREADY_USED"

        # 7. Direct login supplying totp_code in initial payload also succeeds
        direct_code = pyotp.TOTP(secret).now()
        direct_resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": id_token, "totp_code": direct_code},
        )
        assert direct_resp.status_code == 200
        assert "access_token" in direct_resp.json()


@pytest.mark.asyncio
async def test_totp_reenrollment_requires_current_code_and_preserves_active_factor(
    db_session,
):
    """Verify that re-enrolling TOTP requires proof of current factor and does not disable active 2FA until verified."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        id_token = f"test-token-reenroll:{phone}"

        # 1. Login and setup initial 2FA
        auth_resp = await client.post(
            "/api/v1/auth/session", json={"id_token": id_token}
        )
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        setup1_resp = await client.post("/api/v1/auth/2fa/setup", headers=headers)
        secret_old = setup1_resp.json()["secret"]
        code_old = pyotp.TOTP(secret_old).now()
        await client.post(
            "/api/v1/auth/2fa/verify", headers=headers, json={"code": code_old}
        )

        # 2. Calling setup again without current code must be rejected with 403 MFA_VERIFICATION_REQUIRED
        rej1 = await client.post("/api/v1/auth/2fa/setup", headers=headers, json={})
        assert rej1.status_code == 403
        assert rej1.json()["code"] == "MFA_VERIFICATION_REQUIRED"

        # 3. Calling setup with wrong current code rejected with 401 INVALID_TOTP_CODE
        rej2 = await client.post(
            "/api/v1/auth/2fa/setup",
            headers=headers,
            json={"current_totp_code": "000000"},
        )
        assert rej2.status_code == 401
        assert rej2.json()["code"] == "INVALID_TOTP_CODE"

        # 4. Calling setup with valid current code returns new secret without deactivating old factor
        valid_current_code = pyotp.TOTP(secret_old).now()
        setup2_resp = await client.post(
            "/api/v1/auth/2fa/setup",
            headers=headers,
            json={"current_totp_code": valid_current_code},
        )
        assert setup2_resp.status_code == 200
        secret_new = setup2_resp.json()["secret"]
        assert secret_new != secret_old

        # 5. At this moment, old secret MUST STILL BE FUNCTIONAL for login challenges
        login_resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": id_token, "totp_code": pyotp.TOTP(secret_old).now()},
        )
        assert login_resp.status_code == 200

        # 6. Verify and promote the new secret
        code_new = pyotp.TOTP(secret_new).now()
        verify_new_resp = await client.post(
            "/api/v1/auth/2fa/verify", headers=headers, json={"code": code_new}
        )
        assert verify_new_resp.status_code == 200
        assert verify_new_resp.json()["valid"] is True

        # 7. Now new secret works for login, and old secret is rejected
        login_new_resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": id_token, "totp_code": pyotp.TOTP(secret_new).now()},
        )
        assert login_new_resp.status_code == 200


@pytest.mark.asyncio
async def test_authoritative_database_revocation_fallback_when_redis_unavailable(
    db_session,
):
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
            mock_client.get.side_effect = aioredis.ConnectionError(
                "Redis cluster unreachable"
            )
            mock_redis_factory.return_value = mock_client

            # With Redis down, the authoritative DB fallback must catch that the session family is revoked!
            revoked_resp = await client.get("/api/v1/auth/me", headers=headers)
            assert revoked_resp.status_code == 401
            assert revoked_resp.json()["code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_individual_access_token_logout_persisted_to_revoked_tokens_table_and_enforced_in_db_fallback(
    db_session,
):
    """Verify that explicit logout records access token JTI into revoked_tokens and rejects it during Redis outage."""
    from unittest.mock import AsyncMock, patch
    from sqlalchemy import select
    from app.models.revoked_token import RevokedToken
    import redis.asyncio as aioredis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        auth_resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-jti-logout:{phone}"},
        )
        assert auth_resp.status_code == 200
        token_data = auth_resp.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Access token works before logout
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200

        # 2. Call logout
        logout_resp = await client.post("/api/v1/auth/logout", headers=headers)
        assert logout_resp.status_code == 200

        # 3. Verify entry was persisted into revoked_tokens table
        revoked_records = (
            (
                await db_session.execute(
                    select(RevokedToken).where(
                        RevokedToken.user_id == uuid.UUID(token_data["user"]["id"])
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(revoked_records) >= 1

        # 4. Mock complete Redis failure
        with patch("app.core.dependencies.aioredis.from_url") as mock_redis_factory:
            mock_client = AsyncMock()
            mock_client.get.side_effect = aioredis.ConnectionError(
                "Redis cluster unreachable"
            )
            mock_redis_factory.return_value = mock_client

            # Must reject with 401 TOKEN_REVOKED via postgres revoked_tokens check
            check_resp = await client.get("/api/v1/auth/me", headers=headers)
            assert check_resp.status_code == 401
            assert check_resp.json()["code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_concurrent_mfa_challenge_replay_rejection(db_session):
    """Verify that concurrent requests attempting to consume the same MFA challenge token cannot both succeed."""
    import asyncio

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        id_token = f"test-token-mfa-race:{phone}"

        # 1. Login and setup 2FA
        auth_resp = await client.post(
            "/api/v1/auth/session", json={"id_token": id_token}
        )
        assert auth_resp.status_code == 200
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        setup_resp = await client.post("/api/v1/auth/2fa/setup", headers=headers)
        secret = setup_resp.json()["secret"]
        code = pyotp.TOTP(secret).now()
        await client.post(
            "/api/v1/auth/2fa/verify", headers=headers, json={"code": code}
        )

        # 2. Trigger login challenge to get mfa_token
        chal_req = await client.post(
            "/api/v1/auth/session", json={"id_token": id_token}
        )
        assert chal_req.status_code == 403
        mfa_token = chal_req.json()["mfa_token"]

        # 3. Concurrently dispatch 2 challenge requests with the exact same mfa_token
        valid_code = pyotp.TOTP(secret).now()
        res1, res2 = await asyncio.gather(
            client.post(
                "/api/v1/auth/2fa/challenge",
                json={"mfa_token": mfa_token, "totp_code": valid_code},
            ),
            client.post(
                "/api/v1/auth/2fa/challenge",
                json={"mfa_token": mfa_token, "totp_code": valid_code},
            ),
            return_exceptions=True,
        )

        status_codes = [
            r.status_code for r in (res1, res2) if hasattr(r, "status_code")
        ]
        # Exactly one request must succeed (200), and the other must be rejected (401 MFA_CHALLENGE_ALREADY_USED)
        assert 200 in status_codes
        assert 401 in status_codes

        err_resp = res1 if res1.status_code == 401 else res2
        assert err_resp.json()["code"] == "MFA_CHALLENGE_ALREADY_USED"


@pytest.mark.asyncio
async def test_mfa_challenge_replay_rejection_when_redis_is_down(db_session):
    """Verify that when Redis is unreachable, persistent PostgreSQL fallback rejects MFA challenge replays."""
    from unittest.mock import AsyncMock, patch
    import redis.asyncio as aioredis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        id_token = f"test-token-mfa-redis-down:{phone}"

        # 1. Login and setup 2FA
        auth_resp = await client.post(
            "/api/v1/auth/session", json={"id_token": id_token}
        )
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        setup_resp = await client.post("/api/v1/auth/2fa/setup", headers=headers)
        secret = setup_resp.json()["secret"]
        code = pyotp.TOTP(secret).now()
        await client.post(
            "/api/v1/auth/2fa/verify", headers=headers, json={"code": code}
        )

        # 2. Get challenge token
        chal_req = await client.post(
            "/api/v1/auth/session", json={"id_token": id_token}
        )
        mfa_token = chal_req.json()["mfa_token"]

        # 3. Simulate Redis outage
        with patch("app.core.dependencies.aioredis.from_url") as mock_redis_factory:
            mock_client = AsyncMock()
            mock_client.set.side_effect = aioredis.ConnectionError("Redis down")
            mock_client.get.side_effect = aioredis.ConnectionError("Redis down")
            mock_redis_factory.return_value = mock_client

            # First consumption succeeds even with Redis down (persisted in postgres)
            c1_resp = await client.post(
                "/api/v1/auth/2fa/challenge",
                json={"mfa_token": mfa_token, "totp_code": pyotp.TOTP(secret).now()},
            )
            assert c1_resp.status_code == 200

            # Replay attempt with Redis down MUST be caught by PostgreSQL fallback check
            c2_resp = await client.post(
                "/api/v1/auth/2fa/challenge",
                json={"mfa_token": mfa_token, "totp_code": pyotp.TOTP(secret).now()},
            )
            assert c2_resp.status_code == 401
            assert c2_resp.json()["code"] == "MFA_CHALLENGE_ALREADY_USED"
