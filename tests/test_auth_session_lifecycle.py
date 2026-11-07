"""Comprehensive test suite for Phase 02 Stage 2 Authentication and Session Lifecycle.

Validates Requirement R3 and Acceptance Gates 3 & 4:
1. Phone authentication token exchange via POST /api/v1/auth/exchange and legacy route aliases (/session, /firebase-exchange).
2. Single-use refresh token rotation issuing new access and refresh token pairs.
3. Cryptographic reuse detection revoking all user sessions upon replaying an already-revoked refresh token.
4. Session revocation and logout via POST /api/v1/auth/logout with Redis JTI blocklisting.
5. User profile endpoint GET /api/v1/auth/me returning profile, roles, and derived permissions.
6. Zero plaintext database storage of sensitive refresh tokens (SHA-256 hash verification).
"""

import hashlib
import uuid

import pytest
from app.main import app
from app.models.enums import UserRoleEnum
from app.models.session import UserSession
from app.models.users import UserRole
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


def make_headers(token: str | None = None, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Generate request headers with unique client IP to test auth flows cleanly."""
    ip = f"10.{uuid.uuid4().int % 200 + 1}.{uuid.uuid4().int % 200 + 1}.{uuid.uuid4().int % 200 + 1}"
    headers = {"X-Forwarded-For": ip, "User-Agent": "TestClient/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra:
        headers.update(extra)
    return headers


@pytest.mark.asyncio
async def test_phone_auth_exchange_contract_and_aliases(db_session):
    """Verify POST /api/v1/auth/exchange and aliases (/session, /firebase-exchange) return TokenResponse."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Primary endpoint: /api/v1/auth/exchange
        phone_1 = f"+9198{uuid.uuid4().hex[:8]}"
        payload_1 = {
            "id_token": f"test-token-driver:{phone_1}",
            "fcm_token": "fcm_device_token_xyz_123",
            "device_info": "Google Pixel 8 Pro / Android 14",
        }
        resp_1 = await client.post("/api/v1/auth/exchange", json=payload_1, headers=make_headers())
        assert resp_1.status_code == 200, resp_1.text
        data_1 = resp_1.json()
        assert "access_token" in data_1
        assert "refresh_token" in data_1
        assert data_1["token_type"] == "bearer"
        assert data_1["expires_in"] == 3600
        user_1 = data_1["user"]
        assert user_1["phone_number"] == phone_1
        assert "DRIVER" in user_1["roles"]
        assert user_1["status"] == "ACTIVE"
        assert user_1["is_active"] is True
        assert "spaces:search" in user_1["permissions"]
        assert "bookings:hold" in user_1["permissions"]

        # Verify session persisted in DB with SHA-256 hash
        expected_hash = hashlib.sha256(data_1["refresh_token"].encode("utf-8")).hexdigest()
        stmt = select(UserSession).where(UserSession.refresh_token_hash == expected_hash)
        session_rec = (await db_session.execute(stmt)).scalar_one_or_none()
        assert session_rec is not None
        assert session_rec.is_revoked is False
        assert session_rec.device_info == "Google Pixel 8 Pro / Android 14"

        # 2. Legacy alias endpoint: /api/v1/auth/session
        phone_2 = f"+9198{uuid.uuid4().hex[:8]}"
        resp_2 = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-driver:{phone_2}"},
            headers=make_headers(),
        )
        assert resp_2.status_code == 200, resp_2.text
        data_2 = resp_2.json()
        assert data_2["user"]["phone_number"] == phone_2
        assert "access_token" in data_2
        assert "refresh_token" in data_2

        # 3. Mobile alias endpoint: /api/v1/auth/firebase-exchange
        phone_3 = f"+9198{uuid.uuid4().hex[:8]}"
        resp_3 = await client.post(
            "/api/v1/auth/firebase-exchange",
            json={"id_token": f"test-token-driver:{phone_3}"},
            headers=make_headers(),
        )
        assert resp_3.status_code == 200, resp_3.text
        data_3 = resp_3.json()
        assert data_3["user"]["phone_number"] == phone_3


@pytest.mark.asyncio
async def test_phone_auth_exchange_invalid_tokens_rejected(db_session):
    """Verify forged, invalid, or malformed Firebase ID tokens return HTTP 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid signature
        resp_invalid = await client.post(
            "/api/v1/auth/exchange",
            json={"id_token": "completely-invalid-firebase-id-token-xyz"},
            headers=make_headers(),
        )
        assert resp_invalid.status_code == 401
        assert resp_invalid.json()["code"] == "FIREBASE_TOKEN_INVALID"

        # Too short / malformed schema
        resp_short = await client.post(
            "/api/v1/auth/exchange",
            json={"id_token": "short"},
            headers=make_headers(),
        )
        assert resp_short.status_code == 422


@pytest.mark.asyncio
async def test_refresh_token_rotation_single_use(db_session):
    """Verify single-use token rotation: submitting a refresh token yields new tokens and marks old token revoked."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Exchange for initial token pair
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        login_resp = await client.post(
            "/api/v1/auth/exchange",
            json={"id_token": f"test-token-driver:{phone}"},
            headers=make_headers(),
        )
        assert login_resp.status_code == 200
        initial_tokens = login_resp.json()
        access_token_1 = initial_tokens["access_token"]
        refresh_token_1 = initial_tokens["refresh_token"]

        # Verify old session row 1 is active
        hash_1 = hashlib.sha256(refresh_token_1.encode("utf-8")).hexdigest()
        stmt_1 = select(UserSession).where(UserSession.refresh_token_hash == hash_1)
        session_1 = (await db_session.execute(stmt_1)).scalar_one()
        assert session_1.is_revoked is False
        assert session_1.revoked_at is None

        # 2. Present refresh_token_1 to rotate
        rot_resp_1 = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token_1},
            headers=make_headers(),
        )
        assert rot_resp_1.status_code == 200
        tokens_2 = rot_resp_1.json()
        access_token_2 = tokens_2["access_token"]
        refresh_token_2 = tokens_2["refresh_token"]

        # Must issue brand-new tokens
        assert access_token_2 != access_token_1
        assert refresh_token_2 != refresh_token_1

        # Check DB: session 1 is now marked revoked
        await db_session.refresh(session_1)
        assert session_1.is_revoked is True
        assert session_1.revoked_at is not None

        # Check DB: session 2 is active
        hash_2 = hashlib.sha256(refresh_token_2.encode("utf-8")).hexdigest()
        stmt_2 = select(UserSession).where(UserSession.refresh_token_hash == hash_2)
        session_2 = (await db_session.execute(stmt_2)).scalar_one()
        assert session_2.is_revoked is False
        assert session_2.revoked_at is None

        # 3. Rotate a second time with refresh_token_2 -> yields refresh_token_3
        rot_resp_2 = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token_2},
            headers=make_headers(),
        )
        assert rot_resp_2.status_code == 200
        tokens_3 = rot_resp_2.json()
        refresh_token_3 = tokens_3["refresh_token"]
        assert refresh_token_3 != refresh_token_2

        # Check DB: session 2 is now revoked, session 3 is active
        await db_session.refresh(session_2)
        assert session_2.is_revoked is True


@pytest.mark.asyncio
async def test_refresh_token_reuse_detection_revokes_all_sessions(db_session):
    """Verify refresh token reuse detection: replaying an already-rotated token revokes ALL active sessions for that user."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"

        # Step 1: User establishes initial session
        login_resp = await client.post(
            "/api/v1/auth/exchange",
            json={"id_token": f"test-token-driver:{phone}"},
            headers=make_headers(),
        )
        assert login_resp.status_code == 200
        user_id = uuid.UUID(login_resp.json()["user"]["id"])
        refresh_token_1 = login_resp.json()["refresh_token"]

        # Step 2: Legitimate rotation (Token 1 -> Token 2)
        rot_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token_1},
            headers=make_headers(),
        )
        assert rot_resp.status_code == 200
        refresh_token_2 = rot_resp.json()["refresh_token"]

        # Step 3: Establish a second device session for the same user (e.g. tablet login)
        login_resp_device2 = await client.post(
            "/api/v1/auth/exchange",
            json={"id_token": f"test-token-driver:{phone}"},
            headers=make_headers(),
        )
        assert login_resp_device2.status_code == 200
        refresh_token_device2 = login_resp_device2.json()["refresh_token"]

        # Verify in DB: 2 sessions currently active (Token 2 and Device 2)
        active_stmt = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_revoked.is_(False),
        )
        active_sessions = (await db_session.execute(active_stmt)).scalars().all()
        assert len(active_sessions) == 2

        # Step 4: ATTACK / REPLAY: An attacker replays refresh_token_1 (already rotated)
        replay_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token_1},
            headers=make_headers(),
        )
        assert replay_resp.status_code == 401
        problem = replay_resp.json()
        assert problem["code"] == "TOKEN_REVOKED"
        assert problem["detail"] == "Refresh token reuse detected; all sessions revoked"

        # Step 5: Verify ALL active sessions for this user were revoked immediately
        db_session.expire_all()
        active_sessions_after = (await db_session.execute(active_stmt)).scalars().all()
        assert len(active_sessions_after) == 0

        all_stmt = select(UserSession).where(UserSession.user_id == user_id)
        all_sessions = (await db_session.execute(all_stmt)).scalars().all()
        assert len(all_sessions) == 3
        for s in all_sessions:
            assert s.is_revoked is True
            assert s.revoked_at is not None

        # Step 6: Verify that even the previously active Token 2 is now rejected
        token2_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token_2},
            headers=make_headers(),
        )
        assert token2_resp.status_code == 401

        # Step 7: Verify that the device 2 session is also terminated
        device2_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token_device2},
            headers=make_headers(),
        )
        assert device2_resp.status_code == 401


@pytest.mark.asyncio
async def test_session_logout_and_redis_access_token_blocklist(db_session):
    """Verify logout revokes user session and blocklists the access token JTI in Redis."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"

        # Step 1: Login
        login_resp = await client.post(
            "/api/v1/auth/exchange",
            json={"id_token": f"test-token-driver:{phone}"},
            headers=make_headers(),
        )
        assert login_resp.status_code == 200
        auth_data = login_resp.json()
        access_token = auth_data["access_token"]
        refresh_token = auth_data["refresh_token"]

        # Step 2: GET /api/v1/auth/me succeeds with active token
        me_resp_before = await client.get(
            "/api/v1/auth/me",
            headers=make_headers(token=access_token),
        )
        assert me_resp_before.status_code == 200
        assert me_resp_before.json()["phone_number"] == phone

        # Step 3: Logout
        logout_resp = await client.post(
            "/api/v1/auth/logout",
            headers=make_headers(token=access_token),
            json={"refresh_token": refresh_token},
        )
        assert logout_resp.status_code == 200
        assert logout_resp.json()["message"] == "Successfully logged out"

        # Step 4: Verify DB session is marked revoked
        h = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        stmt = select(UserSession).where(UserSession.refresh_token_hash == h)
        sess = (await db_session.execute(stmt)).scalar_one()
        assert sess.is_revoked is True
        assert sess.revoked_at is not None

        # Step 5: Immediate call to /me using the same access token is rejected by Redis blocklist
        me_resp_after = await client.get(
            "/api/v1/auth/me",
            headers=make_headers(token=access_token),
        )
        assert me_resp_after.status_code == 401
        assert me_resp_after.json()["detail"] == "Token has been revoked"
        assert me_resp_after.json()["code"] == "TOKEN_REVOKED"

        # Step 6: Refresh using revoked refresh token is also rejected
        ref_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
            headers=make_headers(),
        )
        assert ref_resp.status_code == 401


@pytest.mark.asyncio
async def test_session_logout_via_header_refresh_token(db_session):
    """Verify logout accepts refresh token in X-Refresh-Token header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"
        login_resp = await client.post(
            "/api/v1/auth/exchange",
            json={"id_token": f"test-token-driver:{phone}"},
            headers=make_headers(),
        )
        assert login_resp.status_code == 200
        auth_data = login_resp.json()
        access_token = auth_data["access_token"]
        refresh_token = auth_data["refresh_token"]

        logout_resp = await client.post(
            "/api/v1/auth/logout",
            headers=make_headers(token=access_token, extra={"X-Refresh-Token": refresh_token}),
        )
        assert logout_resp.status_code == 200

        # Session revoked in DB
        h = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        stmt = select(UserSession).where(UserSession.refresh_token_hash == h)
        sess = (await db_session.execute(stmt)).scalar_one()
        assert sess.is_revoked is True


@pytest.mark.asyncio
async def test_get_current_user_profile_me_and_permissions(db_session):
    """Verify GET /api/v1/auth/me returns user profile and permissions for multiple roles."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"

        # 1. Driver profile
        login_resp = await client.post(
            "/api/v1/auth/exchange",
            json={"id_token": f"test-token-driver:{phone}"},
            headers=make_headers(),
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        user_id = uuid.UUID(login_resp.json()["user"]["id"])

        me_resp = await client.get(
            "/api/v1/auth/me",
            headers=make_headers(token=token),
        )
        assert me_resp.status_code == 200
        profile = me_resp.json()
        assert profile["id"] == str(user_id)
        assert profile["phone_number"] == phone
        assert profile["roles"] == ["DRIVER"]
        assert profile["status"] == "ACTIVE"
        assert profile["is_active"] is True
        assert "spaces:search" in profile["permissions"]
        assert "bookings:hold" in profile["permissions"]

        # 2. Assign OWNER role to user
        owner_role = UserRole(user_id=user_id, role=UserRoleEnum.OWNER)
        db_session.add(owner_role)
        await db_session.commit()

        # Re-fetch profile
        me_resp_dual = await client.get(
            "/api/v1/auth/me",
            headers=make_headers(token=token),
        )
        assert me_resp_dual.status_code == 200
        dual_profile = me_resp_dual.json()
        assert "DRIVER" in dual_profile["roles"]
        assert "OWNER" in dual_profile["roles"]
        assert "properties:create" in dual_profile["permissions"]
        assert "spaces:search" in dual_profile["permissions"]

        # 3. Unauthenticated request rejected with 401
        unauth_resp = await client.get("/api/v1/auth/me", headers=make_headers())
        assert unauth_resp.status_code == 401
        assert unauth_resp.json()["code"] == "MISSING_BEARER_TOKEN"

        # 4. Malformed bearer token rejected with 401
        bad_resp = await client.get(
            "/api/v1/auth/me",
            headers=make_headers(token="not-a-valid-jwt-token"),
        )
        assert bad_resp.status_code == 401


@pytest.mark.asyncio
async def test_user_session_db_integrity_never_stores_plaintext(db_session):
    """Verify that UserSession stores only the SHA-256 hash and never plaintext tokens."""
    phone = f"+9198{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post(
            "/api/v1/auth/exchange",
            json={"id_token": f"test-token-driver:{phone}"},
            headers=make_headers(),
        )
        assert login_resp.status_code == 200
        raw_refresh = login_resp.json()["refresh_token"]
        expected_hash = hashlib.sha256(raw_refresh.encode("utf-8")).hexdigest()

        # Query session row
        stmt = select(UserSession).where(UserSession.refresh_token_hash == expected_hash)
        sess = (await db_session.execute(stmt)).scalar_one()

        # Plaintext token must not match the stored hash
        assert sess.refresh_token_hash != raw_refresh
        assert len(sess.refresh_token_hash) == 64
        assert sess.refresh_token_hash == expected_hash
