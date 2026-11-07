"""Authentication service: Firebase Phone Auth token exchange and PyOTP 2FA."""

import base64
import hashlib
import io
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pyotp
import qrcode
import redis.asyncio as aioredis
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_totp_secret,
    verify_token_type,
)
from app.integrations.firebase import init_firebase, verify_firebase_id_token
from app.models.enums import UserRoleEnum
from app.models.revoked_token import RevokedToken
from app.models.session import UserSession
from app.models.users import AccountStatus, User, UserRole
from app.services.audit_service import AuditService

logger = logging.getLogger("gadispot.auth")

# Backward-compatibility aliases
_init_firebase = init_firebase
verify_firebase_token = verify_firebase_id_token

# Canonical RBAC permissions mapping per PRD §12 and GAP Matrix §3.2
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "DRIVER": [
        "spaces:search",
        "bookings:hold",
        "bookings:read",
        "bookings:extend",
        "vehicles:manage",
        "vehicles:read",
        "access:issue-tokens",
        "payments:create-order",
        "payments:generate-upi-qr",
        "payments:refund:request",
    ],
    "OWNER": [
        "properties:create",
        "properties:spaces:create",
        "properties:schedules:create",
        "spaces:blackout",
        "owner:earnings:read",
    ],
    "GUARD": [
        "access:validate-scan",
        "access:shift-schedule:read",
        "access:manual-admission",
        "access:report-obstruction",
    ],
    "OPERATIONS": [
        "admin:properties:queue",
        "admin:properties:approve",
        "admin:properties:reject",
        "admin:payouts:batch",
        "admin:audit:read",
        "bookings:read",
        "payments:refund:request",
    ],
    "ADMIN": [
        "admin:properties:queue",
        "admin:properties:approve",
        "admin:properties:reject",
        "admin:payouts:batch",
        "admin:audit:read",
        "admin:users:manage",
        "admin:system:configure",
        "bookings:read",
        "payments:refund:request",
        "spaces:search",
    ],
}
# Reconcile PRD alias permissions with canonical definitions
ROLE_PERMISSIONS["SPACE_OWNER"] = ROLE_PERMISSIONS["OWNER"]
ROLE_PERMISSIONS["SECURITY_GUARD"] = ROLE_PERMISSIONS["GUARD"]
ROLE_PERMISSIONS["OPS"] = ROLE_PERMISSIONS["OPERATIONS"]


def get_permissions_for_roles(roles: list[str]) -> list[str]:
    """Derive sorted list of distinct permissions from assigned user roles according to RBAC matrix."""
    perms: set[str] = set()
    for role in roles:
        role_key = role.strip().upper()
        for p in ROLE_PERMISSIONS.get(role_key, []):
            perms.add(p)
    return sorted(perms)


async def exchange_firebase_token_for_session(
    db: AsyncSession,
    id_token: str,
    ip_address: str | None = None,
    device_info: str | None = None,
    totp_code: str | None = None,
) -> dict[str, Any]:
    """Exchange a verified Firebase token for an internal scoped JWT session with race-free user provisioning and session tracking."""
    settings = get_settings()
    claims = verify_firebase_token(id_token)
    phone_number = claims["phone_number"]
    firebase_uid = claims.get("uid")

    # 1. Look up existing users by firebase_uid and phone_number independently
    user_by_uid = None
    if firebase_uid:
        stmt_uid = select(User).where(User.firebase_uid == firebase_uid).options(selectinload(User.roles))
        user_by_uid = (await db.execute(stmt_uid)).scalar_one_or_none()

    stmt_phone = select(User).where(User.phone_number == phone_number).options(selectinload(User.roles))
    user_by_phone = (await db.execute(stmt_phone)).scalar_one_or_none()

    # 2. Strict identity conflict resolution & account takeover prevention
    if user_by_uid and user_by_phone:
        if user_by_uid.id != user_by_phone.id:
            raise ConflictException(
                detail="Identity conflict: verified phone number and Firebase credentials belong to different accounts.",
                title="Identity Conflict",
                code="IDENTITY_CONFLICT",
            )
        user = user_by_uid
    elif user_by_uid and not user_by_phone:
        # Verified phone update on existing Firebase account
        user_by_uid.phone_number = phone_number
        user = user_by_uid
    elif user_by_phone and not user_by_uid:
        if user_by_phone.firebase_uid is not None and user_by_phone.firebase_uid != firebase_uid:
            raise ConflictException(
                detail="This phone number is already registered with a different identity. Please log in with your original account.",
                title="Account Already Linked",
                code="PHONE_ALREADY_LINKED",
            )
        if firebase_uid:
            user_by_phone.firebase_uid = firebase_uid
        user = user_by_phone
    else:
        # First-time driver provisioning (race-free with savepoint)
        try:
            async with db.begin_nested():
                user = User(
                    phone_number=phone_number,
                    firebase_uid=firebase_uid,
                    full_name="Driver User",
                    status=AccountStatus.ACTIVE,
                    is_active=True,
                    last_login_at=datetime.now(timezone.utc),
                )
                db.add(user)
                await db.flush()

                # Assign default DRIVER role
                driver_role = UserRole(user_id=user.id, role=UserRoleEnum.DRIVER)
                db.add(driver_role)
                await db.flush()

            # Re-fetch user with roles
            stmt = select(User).where(User.id == user.id).options(selectinload(User.roles))
            result = await db.execute(stmt)
            user = result.scalar_one()
        except IntegrityError:
            # Handle concurrent registration race: re-fetch committed user
            if firebase_uid:
                stmt_uid = select(User).where(User.firebase_uid == firebase_uid).options(selectinload(User.roles))
                user = (await db.execute(stmt_uid)).scalar_one_or_none()
            if not user:
                stmt_phone = select(User).where(User.phone_number == phone_number).options(selectinload(User.roles))
                user = (await db.execute(stmt_phone)).scalar_one()

    # 3. Update last_login_at
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    # 4. Enforce account status and lifecycle
    if hasattr(user, "status"):
        if user.status == AccountStatus.SUSPENDED:
            raise ForbiddenException(
                detail="Account has been suspended",
                title="Account Suspended",
                code="ACCOUNT_SUSPENDED",
            )
        if user.status == AccountStatus.DISABLED:
            raise ForbiddenException(
                detail="Account is disabled",
                title="Account Disabled",
                code="ACCOUNT_DISABLED",
            )
    if not user.is_active:
        raise ForbiddenException(
            detail="Account is disabled",
            title="Account Inactive",
            code="ACCOUNT_DEACTIVATED",
        )

    # 4b. Enforce Two-Factor Authentication (TOTP) if enrolled
    if getattr(user, "totp_enabled", False):
        if not totp_code:
            challenge_jti = str(uuid.uuid4())
            mfa_token = create_access_token(
                subject=str(user.id),
                claims={
                    "type": "mfa_challenge",
                    "jti": challenge_jti,
                    "phone_number": user.phone_number,
                },
                expires_delta=timedelta(minutes=5),
            )
            raise ForbiddenException(
                detail="Two-factor authentication required. Please verify with your 6-digit TOTP code.",
                title="MFA Required",
                code="MFA_REQUIRED",
                extra={"mfa_token": mfa_token, "mfa_required": True, "expires_in": 300},
            )

        if not user.totp_secret_encrypted:
            raise UnauthorizedException(
                detail="Account configuration error: TOTP is enabled but no secret is enrolled.",
                code="TOTP_CONFIG_ERROR",
            )
        try:
            authoritative_secret = decrypt_totp_secret(user.totp_secret_encrypted)
        except Exception:
            raise UnauthorizedException(
                detail="Failed to decrypt enrolled TOTP credentials.",
                code="TOTP_DECRYPT_ERROR",
            )
        if not verify_totp_code(authoritative_secret, totp_code):
            raise UnauthorizedException(
                detail="Invalid two-factor authentication code.",
                code="INVALID_TOTP_CODE",
            )

    # 5. Extract roles
    role_names: list[str] = user.role_names or [UserRoleEnum.DRIVER.value]

    # 6. Generate scoped access token and cryptographic refresh token with family tracking
    family_id = uuid.uuid4()
    token_claims = {
        "phone_number": user.phone_number,
        "roles": role_names,
        "verified": True,
        "family_id": str(family_id),
    }
    access_token = create_access_token(subject=str(user.id), claims=token_claims)
    refresh_token = create_refresh_token(
        subject=str(user.id),
        claims={"roles": role_names, "family_id": str(family_id)},
    )

    # 7. Persist SHA-256 hash of refresh token into user_sessions table
    token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    session_rec = UserSession(
        user_id=user.id,
        refresh_token_hash=token_hash,
        family_id=family_id,
        device_info=device_info,
        ip_address=ip_address,
        is_revoked=False,
        expires_at=refresh_expires_at,
    )
    db.add(session_rec)
    await db.flush()

    # 8. Record audit event with masked PII
    phone_raw = user.phone_number or ""
    phone_masked = phone_raw[:5] + "*** **" + phone_raw[-3:] if len(phone_raw) >= 10 else "[MASKED]"
    await AuditService.log_event(
        db=db,
        action="AUTH_SESSION_EXCHANGED",
        resource_type="USER",
        resource_id=str(user.id),
        actor_id=user.id,
        details={"phone_masked": phone_masked, "roles": role_names, "family_id": str(family_id)},
        ip_address=ip_address,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "phone_number": user.phone_number,
            "full_name": user.full_name,
            "email": user.email,
            "roles": role_names,
            "is_active": user.is_active,
            "status": user.status.value if hasattr(user.status, "value") else str(user.status),
            "firebase_uid": user.firebase_uid,
            "permissions": get_permissions_for_roles(role_names),
        },
    }


async def verify_mfa_challenge(
    db: AsyncSession,
    mfa_token: str,
    totp_code: str,
    redis: aioredis.Redis | None = None,
    ip_address: str | None = None,
    device_info: str | None = None,
) -> dict[str, Any]:
    """Verify MFA challenge token and TOTP code with atomic one-time challenge consumption to establish session."""
    settings = get_settings()
    claims = decode_token(mfa_token)
    if claims.get("type") != "mfa_challenge":
        raise UnauthorizedException(
            detail="Invalid challenge token",
            code="INVALID_CHALLENGE_TOKEN",
        )

    challenge_jti = claims.get("jti")
    if not challenge_jti:
        raise UnauthorizedException(
            detail="Malformed challenge token: missing unique identifier.",
            code="INVALID_CHALLENGE_TOKEN",
        )

    # 1. Check if challenge has already been consumed in Redis or Database
    if redis:
        try:
            is_consumed = await redis.get(f"mfa:challenge:consumed:{challenge_jti}")
            if is_consumed:
                logger.warning("MFA challenge replay detected via Redis for JTI %s", challenge_jti)
                raise UnauthorizedException(
                    detail="MFA challenge token has already been consumed.",
                    code="MFA_CHALLENGE_ALREADY_USED",
                )
        except aioredis.RedisError:
            pass

    db_check = await db.execute(select(RevokedToken).where(RevokedToken.jti == challenge_jti))
    if db_check.scalar_one_or_none():
        logger.warning("MFA challenge replay detected via database for JTI %s", challenge_jti)
        raise UnauthorizedException(
            detail="MFA challenge token has already been consumed.",
            code="MFA_CHALLENGE_ALREADY_USED",
        )

    user_id_str = claims.get("sub")
    if not user_id_str:
        raise UnauthorizedException(
            detail="Malformed challenge token",
            code="INVALID_CHALLENGE_TOKEN",
        )

    user_uuid = uuid.UUID(user_id_str)
    stmt = select(User).where(User.id == user_uuid).options(selectinload(User.roles))
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise UnauthorizedException(detail="User no longer exists", code="USER_NOT_FOUND")

    if not user.totp_enabled or not user.totp_secret_encrypted:
        raise UnauthorizedException(
            detail="TOTP is not configured for this user",
            code="TOTP_NOT_CONFIGURED",
        )

    try:
        authoritative_secret = decrypt_totp_secret(user.totp_secret_encrypted)
    except Exception:
        raise UnauthorizedException(
            detail="Failed to decrypt TOTP credentials",
            code="TOTP_DECRYPT_ERROR",
        )

    if not verify_totp_code(authoritative_secret, totp_code):
        raise UnauthorizedException(
            detail="Invalid two-factor authentication code.",
            code="INVALID_TOTP_CODE",
        )

    # 2. TOTP code is valid: atomically consume the challenge token (Redis SET NX + DB primary key lock)
    now_ts = int(time.time())
    exp_ts = int(claims.get("exp", now_ts + 300))
    challenge_ttl = max(1, exp_ts - now_ts)
    if redis:
        try:
            was_set = await redis.set(f"mfa:challenge:consumed:{challenge_jti}", "1", nx=True, ex=challenge_ttl)
            if not was_set:
                logger.warning("Concurrent MFA challenge replay detected via Redis for JTI %s", challenge_jti)
                raise UnauthorizedException(
                    detail="MFA challenge token has already been consumed.",
                    code="MFA_CHALLENGE_ALREADY_USED",
                )
        except aioredis.RedisError:
            pass

    now_utc = datetime.now(timezone.utc)
    exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
    try:
        async with db.begin_nested():
            consumed_entry = RevokedToken(
                jti=challenge_jti,
                user_id=user.id,
                family_id=None,
                expires_at=exp_dt,
                revoked_at=now_utc,
            )
            db.add(consumed_entry)
            await db.flush()
    except IntegrityError:
        logger.warning("Concurrent MFA challenge consumption race detected for JTI %s", challenge_jti)
        raise UnauthorizedException(
            detail="MFA challenge token has already been consumed.",
            code="MFA_CHALLENGE_ALREADY_USED",
        )

    # 4. Enforce account lifecycle & status
    if hasattr(user, "status"):
        if user.status == AccountStatus.SUSPENDED:
            raise ForbiddenException(detail="Account has been suspended", code="ACCOUNT_SUSPENDED")
        if user.status == AccountStatus.DISABLED:
            raise ForbiddenException(detail="Account is disabled", code="ACCOUNT_DISABLED")
    if not user.is_active:
        raise ForbiddenException(detail="Account is disabled", code="ACCOUNT_DEACTIVATED")

    role_names: list[str] = user.role_names or [UserRoleEnum.DRIVER.value]

    family_id = uuid.uuid4()
    token_claims = {
        "phone_number": user.phone_number,
        "roles": role_names,
        "verified": True,
        "family_id": str(family_id),
    }
    access_token = create_access_token(subject=str(user.id), claims=token_claims)
    refresh_token = create_refresh_token(
        subject=str(user.id),
        claims={"roles": role_names, "family_id": str(family_id)},
    )
    token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    session_rec = UserSession(
        user_id=user.id,
        refresh_token_hash=token_hash,
        family_id=family_id,
        device_info=device_info,
        ip_address=ip_address,
        is_revoked=False,
        expires_at=refresh_expires_at,
    )
    db.add(session_rec)
    await db.flush()

    await AuditService.log_event(
        db=db,
        action="AUTH_MFA_CHALLENGE_VERIFIED",
        resource_type="USER",
        resource_id=str(user.id),
        actor_id=user.id,
        details={"challenge_jti": challenge_jti, "family_id": str(family_id)},
        ip_address=ip_address,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "phone_number": user.phone_number,
            "full_name": user.full_name,
            "email": user.email,
            "roles": role_names,
            "is_active": user.is_active,
            "status": user.status.value if hasattr(user.status, "value") else str(user.status),
            "firebase_uid": user.firebase_uid,
            "permissions": get_permissions_for_roles(role_names),
        },
    }


async def refresh_session_tokens(
    db: AsyncSession,
    refresh_token: str,
    redis: aioredis.Redis | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    """Issue a fresh access token from a valid refresh token with single-use rotation, reuse detection, and family revocation."""
    settings = get_settings()
    payload = decode_token(refresh_token)
    verify_token_type(payload, "refresh")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException(detail="Invalid token subject", code="INVALID_TOKEN")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException(detail="Malformed user ID in token", code="INVALID_TOKEN")

    # 1. Compute SHA-256 hash of presented refresh token
    token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

    # 2. Check Redis for family revocation if available
    family_id_str = payload.get("family_id")
    if redis and family_id_str:
        try:
            is_family_revoked = await redis.get(f"jwt:family:revoked:{family_id_str}")
            if is_family_revoked:
                raise UnauthorizedException(
                    detail="Token family has been revoked due to security compromise.",
                    code="TOKEN_REVOKED",
                )
        except aioredis.RedisError:
            pass

    # 3. Query UserSession record with row-level lock for atomic rotation
    stmt = select(UserSession).where(UserSession.refresh_token_hash == token_hash).with_for_update()
    result = await db.execute(stmt)
    session_rec = result.scalar_one_or_none()

    if not session_rec:
        raise UnauthorizedException(detail="Invalid or unrecognized refresh token", code="INVALID_TOKEN")

    # 4. Token Reuse Detection & Concurrency Grace Period (OAuth 2.0 BCP §4.14.2)
    if session_rec.is_revoked or session_rec.revoked_at is not None:
        now = datetime.now(timezone.utc)
        elapsed_seconds = (now - (session_rec.revoked_at or now)).total_seconds()

        # Check if rotated within legitimate concurrent rotation grace period
        if elapsed_seconds <= settings.REFRESH_ROTATION_GRACE_PERIOD_SECONDS and session_rec.family_id:
            succ_stmt = (
                select(UserSession)
                .where(
                    UserSession.family_id == session_rec.family_id,
                    UserSession.is_revoked.is_(False),
                    UserSession.expires_at > now,
                )
                .order_by(UserSession.created_at.desc())
                .limit(1)
            )
            succ_res = await db.execute(succ_stmt)
            active_successor = succ_res.scalar_one_or_none()
            if active_successor:
                logger.info(
                    "Concurrent refresh request detected for token %s within grace window (%.2fs); family preserved",
                    token_hash[:16],
                    elapsed_seconds,
                )
                raise ConflictException(
                    detail="This refresh token was recently rotated by a concurrent request. Please use the newly issued credentials.",
                    title="Token Recently Rotated",
                    code="TOKEN_ALREADY_ROTATED",
                )

        # REUSE DETECTED OUTSIDE GRACE PERIOD: Revoke active sessions strictly belonging to this compromised family_id
        if session_rec.family_id:
            await db.execute(
                update(UserSession)
                .where(UserSession.family_id == session_rec.family_id, UserSession.is_revoked.is_(False))
                .values(is_revoked=True, revoked_at=now)
            )
        else:
            session_rec.is_revoked = True
            session_rec.revoked_at = now
        await db.flush()

        if redis and session_rec.family_id:
            try:
                await redis.set(f"jwt:family:revoked:{session_rec.family_id}", "1", ex=30 * 86400)
            except aioredis.RedisError:
                pass

        await AuditService.log_event(
            db=db,
            action="AUTH_TOKEN_REUSE_DETECTED",
            resource_type="SESSION",
            resource_id=str(session_rec.id),
            actor_id=session_rec.user_id,
            details={
                "family_id": str(session_rec.family_id) if session_rec.family_id else None,
                "compromised_hash": token_hash[:16],
                "family_sessions_revoked": True,
            },
            ip_address=ip_address,
        )
        await db.commit()
        raise UnauthorizedException(
            detail="Refresh token reuse detected; session family revoked",
            code="TOKEN_REVOKED",
        )

    # 5. Expiration check
    if session_rec.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedException(detail="Refresh token has expired", code="TOKEN_EXPIRED")

    # 6. Mark currently presented refresh token as consumed (Single-use rotation)
    session_rec.is_revoked = True
    session_rec.revoked_at = datetime.now(timezone.utc)
    await db.flush()

    # 7. Hydrate user and verify active status
    user_stmt = select(User).where(User.id == user_uuid).options(selectinload(User.roles))
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()

    if not user:
        raise UnauthorizedException(detail="User no longer exists", code="USER_NOT_FOUND")

    # Enforce account lifecycle & status
    if hasattr(user, "status"):
        if user.status == AccountStatus.SUSPENDED:
            raise ForbiddenException(
                detail="Account has been suspended",
                title="Account Suspended",
                code="ACCOUNT_SUSPENDED",
            )
        if user.status == AccountStatus.DISABLED:
            raise ForbiddenException(
                detail="Account is disabled",
                title="Account Disabled",
                code="ACCOUNT_DISABLED",
            )

    if not user.is_active:
        raise ForbiddenException(
            detail="Account is disabled",
            title="Account Inactive",
            code="ACCOUNT_DEACTIVATED",
        )

    role_names: list[str] = user.role_names or [UserRoleEnum.DRIVER.value]

    # 8. Issue fresh access token and new rotating refresh token under same family_id
    family_id = session_rec.family_id or uuid.uuid4()
    token_claims = {
        "phone_number": user.phone_number,
        "roles": role_names,
        "verified": True,
        "family_id": str(family_id),
    }
    new_access_token = create_access_token(subject=str(user.id), claims=token_claims)
    new_refresh_token = create_refresh_token(
        subject=str(user.id),
        claims={"roles": role_names, "family_id": str(family_id)},
    )

    # 9. Store new session row
    new_token_hash = hashlib.sha256(new_refresh_token.encode("utf-8")).hexdigest()
    new_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    new_session = UserSession(
        user_id=user.id,
        refresh_token_hash=new_token_hash,
        family_id=family_id,
        device_info=session_rec.device_info,
        ip_address=ip_address or session_rec.ip_address,
        is_revoked=False,
        expires_at=new_expires_at,
    )
    db.add(new_session)
    await db.flush()

    await AuditService.log_event(
        db=db,
        action="AUTH_TOKEN_REFRESHED",
        resource_type="SESSION",
        resource_id=str(new_session.id),
        actor_id=user.id,
        details={"family_id": str(family_id)},
        ip_address=ip_address,
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "phone_number": user.phone_number,
            "full_name": user.full_name,
            "email": user.email,
            "roles": role_names,
            "is_active": user.is_active,
            "status": user.status.value if hasattr(user.status, "value") else str(user.status),
            "firebase_uid": user.firebase_uid,
            "permissions": get_permissions_for_roles(role_names),
        },
    }


async def logout_user_session(
    db: AsyncSession,
    user: User,
    access_token_jti: str | None = None,
    access_token_ttl: int = 3600,
    refresh_token: str | None = None,
    redis: aioredis.Redis | None = None,
    ip_address: str | None = None,
) -> None:
    """Explicitly terminate user session, revoke refresh token(s), and blocklist access token in Redis."""
    now = datetime.now(timezone.utc)

    # 1. Invalidate specific refresh token if supplied, otherwise invalidate all active sessions
    if refresh_token:
        h = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        await db.execute(
            update(UserSession).where(UserSession.refresh_token_hash == h).values(is_revoked=True, revoked_at=now)
        )
    else:
        await db.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.is_revoked.is_(False))
            .values(is_revoked=True, revoked_at=now)
        )

    # 2. Blocklist access token JTI in Redis with TTL matching remaining access token lifespan
    if access_token_jti and redis:
        try:
            await redis.set(f"jwt:blocklist:{access_token_jti}", "1", ex=access_token_ttl)
        except aioredis.RedisError:
            pass

    # 3. Persist revoked JTI into PostgreSQL for authoritative fallback during Redis failure
    if access_token_jti:
        expires_at = now + timedelta(seconds=access_token_ttl)
        revoked_rec = RevokedToken(
            jti=access_token_jti,
            user_id=user.id,
            expires_at=expires_at,
            revoked_at=now,
        )
        db.add(revoked_rec)

    await db.flush()

    await AuditService.log_event(
        db=db,
        action="AUTH_LOGOUT",
        resource_type="USER",
        resource_id=str(user.id),
        actor_id=user.id,
        details={"logout_scope": "specific_token" if refresh_token else "all_active_sessions"},
        ip_address=ip_address,
    )


async def switch_user_role(
    db: AsyncSession,
    user: User,
    target_role: str,
    ip_address: str | None = None,
) -> dict[str, Any]:
    """Switch active viewport role for users who hold multiple assigned roles (e.g. Driver <-> Space Owner)."""
    normalized_target = target_role.strip().upper()
    user_role_names = user.role_names

    allowed_switch_roles = {"DRIVER", "SPACE_OWNER", "OWNER"}
    if normalized_target not in allowed_switch_roles:
        raise ForbiddenException(
            detail=f"Role '{target_role}' cannot be activated via dynamic role switcher.",
            title="Role Switch Prohibited",
            code="ROLE_SWITCH_PROHIBITED",
        )

    has_role = normalized_target in user_role_names or (
        normalized_target in ("SPACE_OWNER", "OWNER") and any(r in ("SPACE_OWNER", "OWNER") for r in user_role_names)
    )

    if not has_role:
        raise ForbiddenException(
            detail=f"User does not possess authorized clearance for role '{target_role}'.",
            title="Insufficient Role Clearance",
            code="ROLE_NOT_ASSIGNED",
        )

    await AuditService.log_event(
        db=db,
        action="ROLE_SWITCHED",
        resource_type="USER",
        resource_id=str(user.id),
        actor_id=user.id,
        details={"new_active_role": normalized_target, "previous_roles": user_role_names},
        ip_address=ip_address,
    )

    return {
        "active_role": normalized_target,
        "allowed_roles": user_role_names,
        "message": f"Successfully switched active viewport to {normalized_target}.",
    }


# ============================================================================
# PyOTP Operations 2FA Integration (RFC 6238 TOTP)
# ============================================================================


def generate_totp_secret() -> str:
    """Generate a high-entropy Base32 secret for RFC 6238 TOTP."""
    return pyotp.random_base32()


def get_totp_provisioning_uri(secret: str, user_identifier: str) -> str:
    """Generate standard otpauth:// URI for mobile authenticator apps."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=user_identifier, issuer_name="Gadispot Operations")


def generate_totp_qr_base64(provisioning_uri: str) -> str:
    """Generate a Base64-encoded PNG data URL representing the TOTP provisioning QR code."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_png = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_png}"


def verify_totp_code(secret: str, code: str, valid_window: int = 1) -> bool:
    """Verify an RFC 6238 TOTP 6-digit code with +/- 30s clock drift tolerance."""
    if not code or len(code.strip()) != 6 or not code.isdigit():
        return False
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(code.strip(), valid_window=valid_window))
