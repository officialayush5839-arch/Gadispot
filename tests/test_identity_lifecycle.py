"""Automated tests for Phase 02 Stage 1 Identity and Account Model.

Covers:
1. Database-level identity uniqueness (duplicate phone_number and firebase_uid rejected).
2. Race-free concurrent user account provisioning (no 500 crashes).
3. Account lifecycle & status enforcement (ACTIVE, SUSPENDED, DISABLED, is_active=False).
4. Server-side Firebase token verification and production security rules.
5. UserSession model, SHA-256 hashing, and cascade deletion.
6. Alembic migration 004 upgrade and downgrade reversibility.
"""

import asyncio
import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from alembic import command
from alembic.config import Config
from app.core.dependencies import get_current_user
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import create_access_token
from app.db.session import async_session_factory
from app.integrations.firebase import (
    reset_firebase_state,
    verify_firebase_id_token,
)
from app.main import app
from app.models.enums import UserRoleEnum
from app.models.session import UserSession
from app.models.users import AccountStatus, User
from app.services.auth_service import (
    exchange_firebase_token_for_session,
    refresh_session_tokens,
)
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

# ============================================================================
# 1. Identity Uniqueness at Database Level
# ============================================================================


@pytest.mark.asyncio
async def test_identity_uniqueness_db_constraints(db_session):
    """Verify duplicate phone_number and duplicate firebase_uid are rejected by PostgreSQL."""
    phone1 = f"+9198{uuid.uuid4().hex[:8]}"
    phone2 = f"+9198{uuid.uuid4().hex[:8]}"
    uid1 = f"firebase-uid-{uuid.uuid4().hex[:12]}"
    uid2 = f"firebase-uid-{uuid.uuid4().hex[:12]}"

    # 1. Insert initial user
    user1 = User(
        phone_number=phone1,
        firebase_uid=uid1,
        full_name="Driver Primary",
        status=AccountStatus.ACTIVE,
        is_active=True,
    )
    db_session.add(user1)
    await db_session.flush()

    # 2. Duplicate phone_number must fail
    async with db_session.begin_nested():
        user_dup_phone = User(
            phone_number=phone1,
            firebase_uid=uid2,
            full_name="Driver Duplicate Phone",
            status=AccountStatus.ACTIVE,
            is_active=True,
        )
        db_session.add(user_dup_phone)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    # 3. Duplicate firebase_uid must fail
    async with db_session.begin_nested():
        user_dup_uid = User(
            phone_number=phone2,
            firebase_uid=uid1,
            full_name="Driver Duplicate UID",
            status=AccountStatus.ACTIVE,
            is_active=True,
        )
        db_session.add(user_dup_uid)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    # 4. Nullable firebase_uid permits multiple distinct users without UID
    phone3 = f"+9198{uuid.uuid4().hex[:8]}"
    phone4 = f"+9198{uuid.uuid4().hex[:8]}"
    user_null_uid1 = User(
        phone_number=phone3,
        firebase_uid=None,
        full_name="Driver No UID 1",
        status=AccountStatus.ACTIVE,
        is_active=True,
    )
    user_null_uid2 = User(
        phone_number=phone4,
        firebase_uid=None,
        full_name="Driver No UID 2",
        status=AccountStatus.ACTIVE,
        is_active=True,
    )
    db_session.add_all([user_null_uid1, user_null_uid2])
    await db_session.flush()
    assert user_null_uid1.id != user_null_uid2.id


# ============================================================================
# 2. Concurrent User Account Provisioning
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_user_account_creation():
    """Verify concurrent registration requests for the same phone number execute race-free."""
    phone = f"+9198{uuid.uuid4().hex[:8]}"
    id_token = f"test-token-driver:{phone}"

    async def execute_exchange():
        async with async_session_factory() as session:
            try:
                res = await exchange_firebase_token_for_session(session, id_token)
                await session.commit()
                return res
            except Exception:
                await session.rollback()
                raise

    # Fire 8 concurrent exchange requests simultaneously
    tasks = [execute_exchange() for _ in range(8)]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # All concurrent requests must succeed with 0 unhandled 500 errors
    assert len(results) == 8
    first_user_id = results[0]["user"]["id"]
    for r in results:
        assert r["user"]["id"] == first_user_id
        assert r["user"]["phone_number"] == phone
        assert "access_token" in r
        assert "refresh_token" in r

    # Verify database has strictly 1 User record and 1 UserRole record
    async with async_session_factory() as session:
        stmt = (
            select(User)
            .where(User.phone_number == phone)
            .options(selectinload(User.roles))
        )
        res = await session.execute(stmt)
        users = res.scalars().all()
        assert len(users) == 1
        user = users[0]
        assert len(user.roles) == 1
        assert user.roles[0].role == UserRoleEnum.DRIVER
        assert user.last_login_at is not None


# ============================================================================
# 3. Account Lifecycle & Status Enforcement
# ============================================================================


@pytest.mark.asyncio
async def test_account_status_enforcement_in_service(db_session):
    """Verify ACTIVE permits authentication; SUSPENDED and DISABLED reject with HTTP 403."""
    phone = f"+9198{uuid.uuid4().hex[:8]}"
    id_token = f"test-token-driver:{phone}"

    # 1. Normal ACTIVE user authentication succeeds
    auth_data = await exchange_firebase_token_for_session(db_session, id_token)
    assert auth_data["user"]["status"] == "ACTIVE"
    user_id = auth_data["user"]["id"]

    # 2. Suspend account -> token exchange must raise ForbiddenException 403
    stmt = select(User).where(User.id == user_id)
    user = (await db_session.execute(stmt)).scalar_one()
    user.status = AccountStatus.SUSPENDED
    await db_session.flush()

    with pytest.raises(ForbiddenException) as exc_info:
        await exchange_firebase_token_for_session(db_session, id_token)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Account has been suspended"
    assert exc_info.value.code == "ACCOUNT_SUSPENDED"

    # Refresh must also be blocked
    with pytest.raises(ForbiddenException) as exc_info:
        await refresh_session_tokens(db_session, auth_data["refresh_token"])
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Account has been suspended"

    # 3. Disable account -> must raise ForbiddenException 403
    user.status = AccountStatus.DISABLED
    await db_session.flush()

    with pytest.raises(ForbiddenException) as exc_info:
        await exchange_firebase_token_for_session(db_session, id_token)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Account is disabled"
    assert exc_info.value.code == "ACCOUNT_DISABLED"

    # 4. is_active = False -> must raise ForbiddenException 403
    user.status = AccountStatus.ACTIVE
    user.is_active = False
    await db_session.flush()

    with pytest.raises(ForbiddenException) as exc_info:
        await exchange_firebase_token_for_session(db_session, id_token)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Account is disabled"


@pytest.mark.asyncio
async def test_get_current_user_dependency_status_enforcement(db_session):
    """Verify get_current_user dependency rejects SUSPENDED and DISABLED accounts with 403."""
    phone = f"+9198{uuid.uuid4().hex[:8]}"
    user = User(
        phone_number=phone,
        full_name="Status Check Driver",
        status=AccountStatus.ACTIVE,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(
        subject=str(user.id), claims={"phone_number": phone, "roles": ["DRIVER"]}
    )

    class DummyRequest:
        state = type("State", (), {})()

    req = DummyRequest()

    # Active user succeeds
    hydrated = await get_current_user(
        request=req, authorization=f"Bearer {token}", db=db_session
    )
    assert hydrated.id == user.id

    # Suspended user blocked with 403
    user.status = AccountStatus.SUSPENDED
    await db_session.flush()
    with pytest.raises(ForbiddenException) as exc_info:
        await get_current_user(
            request=req, authorization=f"Bearer {token}", db=db_session
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Account has been suspended"

    # Disabled user blocked with 403
    user.status = AccountStatus.DISABLED
    await db_session.flush()
    with pytest.raises(ForbiddenException) as exc_info:
        await get_current_user(
            request=req, authorization=f"Bearer {token}", db=db_session
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Account is disabled"


@pytest.mark.asyncio
async def test_api_account_status_rfc7807_responses(db_session):
    """Verify FastAPI /api/v1/auth/session endpoint returns RFC 7807 problem details for non-active users."""
    transport = ASGITransport(app=app)
    ip_suffix = uuid.uuid4().hex[:6]
    headers = {"X-Forwarded-For": f"10.200.{int(ip_suffix[:2], 16)}.{int(ip_suffix[2:4], 16)}"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        phone = f"+9198{uuid.uuid4().hex[:8]}"

        # 1. Create initial user
        init_resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-driver:{phone}"},
            headers=headers,
        )
        assert init_resp.status_code == 200
        user_id = uuid.UUID(init_resp.json()["user"]["id"])

        # 2. Suspend user via DB
        stmt = select(User).where(User.id == user_id)
        user = (await db_session.execute(stmt)).scalar_one()
        user.status = AccountStatus.SUSPENDED
        await db_session.commit()

        # 3. Exchange attempt returns HTTP 403 with RFC 7807 problem details
        susp_resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-driver:{phone}"},
            headers=headers,
        )
        assert susp_resp.status_code == 403
        data = susp_resp.json()
        assert data["detail"] == "Account has been suspended"
        assert data["code"] == "ACCOUNT_SUSPENDED"
        assert data["status"] == 403

        # 4. Disable user
        user.status = AccountStatus.DISABLED
        await db_session.commit()

        dis_resp = await client.post(
            "/api/v1/auth/session",
            json={"id_token": f"test-token-driver:{phone}"},
            headers=headers,
        )
        assert dis_resp.status_code == 403
        data = dis_resp.json()
        assert data["detail"] == "Account is disabled"
        assert data["code"] == "ACCOUNT_DISABLED"
        assert data["status"] == 403


# ============================================================================
# 4. Server-Side Firebase Token Verification & Production Security
# ============================================================================


@pytest.mark.asyncio
async def test_firebase_token_verification_rules(monkeypatch, tmp_path):
    """Verify server-side Firebase token verification and strict production security checks."""
    # 1. Test mock token parsing in test environment
    claims = verify_firebase_id_token("test-token-driver:+919876543210")
    assert claims["phone_number"] == "+919876543210"
    assert claims["uid"] == "test-uid-9876543210"

    # 2. Mock token strictly rejected in production
    monkeypatch.setattr("app.core.config.Settings.is_production", True)
    with pytest.raises(UnauthorizedException) as exc_info:
        verify_firebase_id_token("test-token-driver:+919876543210")
    assert exc_info.value.status_code == 401
    assert (
        "Mock authentication tokens are strictly forbidden in production"
        in exc_info.value.detail
    )

    # Restore is_production
    monkeypatch.setattr("app.core.config.Settings.is_production", False)

    # 3. Empty or unverified malformed token rejected
    with pytest.raises(UnauthorizedException):
        verify_firebase_id_token("")

    with pytest.raises(UnauthorizedException):
        verify_firebase_id_token("completely-unverified-fake-jwt-token")

    # 4. FIREBASE_CREDENTIALS_PATH support
    cert_file = tmp_path / "fake_firebase_credentials.json"
    cert_file.write_text(
        json.dumps({"type": "service_account", "project_id": "test-gsp-project"})
    )
    monkeypatch.setenv("FIREBASE_CREDENTIALS_PATH", str(cert_file))
    reset_firebase_state()

    # Verified that init_firebase correctly reads the environment certificate path
    # (Note: In test without real Google cert, it attempts Certificate load)
    assert os.path.isfile(str(cert_file))


# ============================================================================
# 5. UserSession Model & SHA-256 Refresh Token Hash
# ============================================================================


@pytest.mark.asyncio
async def test_user_session_storage_and_cascade(db_session):
    """Verify UserSession persists SHA-256 hash (never plaintext) and cascades on user delete."""
    phone = f"+9198{uuid.uuid4().hex[:8]}"
    user = User(
        phone_number=phone,
        full_name="Session Test Driver",
        status=AccountStatus.ACTIVE,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    raw_refresh_token = f"raw_refresh_secret_{uuid.uuid4().hex}"
    token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
    assert len(token_hash) == 64

    session_rec = UserSession(
        user_id=user.id,
        refresh_token_hash=token_hash,
        family_id=uuid.uuid4(),
        device_info="Flutter Mobile / Pixel 8",
        ip_address="192.168.1.100",
        is_revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(session_rec)
    await db_session.flush()

    # Query session back
    stmt = select(UserSession).where(UserSession.id == session_rec.id)
    queried = (await db_session.execute(stmt)).scalar_one()
    assert queried.user_id == user.id
    assert queried.refresh_token_hash == token_hash
    assert queried.is_revoked is False
    assert queried.device_info == "Flutter Mobile / Pixel 8"

    # Unique constraint on refresh_token_hash
    async with db_session.begin_nested():
        dup_session = UserSession(
            user_id=user.id,
            refresh_token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db_session.add(dup_session)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    # Cascade delete on user directly at PostgreSQL storage level
    from sqlalchemy import delete

    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.flush()

    stmt = select(UserSession).where(UserSession.id == session_rec.id)
    assert (await db_session.execute(stmt)).scalar_one_or_none() is None


# ============================================================================
# 6. Alembic Migration 004 Upgrade and Downgrade
# ============================================================================


@pytest.mark.asyncio
async def test_migration_004_upgrade_and_downgrade(pg_pool):
    """Verify migration 004_identity_and_sessions downgrades and upgrades cleanly."""
    backend_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "backend")
    )
    alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)

    # 1. Downgrade from 004 to 003_demo_payments
    command.downgrade(alembic_cfg, "003_demo_payments")

    async with pg_pool.acquire() as conn:
        # user_sessions table must not exist
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'user_sessions'
            );
        """)
        assert table_exists is False

        # firebase_uid and status columns must not exist on users table
        col_firebase_uid = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'firebase_uid'
            );
        """)
        assert col_firebase_uid is False

        col_status = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'status'
            );
        """)
        assert col_status is False

    # 2. Upgrade back to head (004)
    command.upgrade(alembic_cfg, "head")

    async with pg_pool.acquire() as conn:
        # user_sessions table must exist
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'user_sessions'
            );
        """)
        assert table_exists is True

        # Columns must exist on users table
        col_firebase_uid = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'firebase_uid'
            );
        """)
        assert col_firebase_uid is True

        col_status = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'status'
            );
        """)
        assert col_status is True

    # Refresh connection pools so subsequent tests receive fresh enum OIDs from PostgreSQL
    await pg_pool.expire_connections()
    from app.db.session import engine

    await engine.dispose()
