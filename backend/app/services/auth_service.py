"""Authentication service: Firebase Phone Auth token exchange and PyOTP 2FA."""

import base64
import hashlib
import io
import logging
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
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
)
from app.integrations.firebase import init_firebase, verify_firebase_id_token
from app.models.enums import UserRoleEnum
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
    "SPACE_OWNER": [
        "properties:create",
        "properties:spaces:create",
        "properties:schedules:create",
        "spaces:blackout",
        "owner:earnings:read",
    ],
    "OWNER": [
        "properties:create",
        "properties:spaces:create",
        "properties:schedules:create",
        "spaces:blackout",
        "owner:earnings:read",
    ],
    "SECURITY_GUARD": [
        "access:validate-scan",
        "access:shift-schedule:read",
        "access:manual-admission",
        "access:report-obstruction",
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
        "*",
    ],
}


def get_permissions_for_roles(roles: list[str]) -> list[str]:
    """Derive sorted list of distinct permissions from assigned user roles according to RBAC matrix."""
    perms: set[str] = set()
    for role in roles:
        role_key = role.strip().upper()
        if role_key == "ADMIN":
            return ["*"]
        for p in ROLE_PERMISSIONS.get(role_key, []):
            perms.add(p)
    return sorted(perms)


async def exchange_firebase_token_for_session(
    db: AsyncSession,
    id_token: str,
    ip_address: str | None = None,
    device_info: str | None = None,
) -> dict[str, Any]:
    """Exchange a verified Firebase token for an internal scoped JWT session with race-free user provisioning and session tracking."""
    settings = get_settings()
    claims = verify_firebase_token(id_token)
    phone_number = claims["phone_number"]
    firebase_uid = claims.get("uid")

    # 1. Look up existing user by phone_number or firebase_uid with roles eagerly loaded
    lookup_conditions = [User.phone_number == phone_number]
    if firebase_uid:
        lookup_conditions.append(User.firebase_uid == firebase_uid)

    stmt = select(User).where(or_(*lookup_conditions)).options(selectinload(User.roles))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # 2. Provision user if first-time driver login (race-free with savepoint)
    if not user:
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
            # Handle concurrent registration race: another request committed first
            stmt = select(User).where(or_(*lookup_conditions)).options(selectinload(User.roles))
            result = await db.execute(stmt)
            user = result.scalar_one()

    # 3. Update firebase_uid and last_login_at if changed
    if firebase_uid and user.firebase_uid != firebase_uid:
        user.firebase_uid = firebase_uid
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

    # 5. Extract roles
    role_names: list[str] = [r.role.value if hasattr(r.role, "value") else str(r.role) for r in user.roles]
    if not role_names:
        role_names = [UserRoleEnum.DRIVER.value]

    # 6. Generate scoped access token and cryptographic refresh token with family tracking
    family_id = uuid.uuid4()
    token_claims = {
        "phone_number": user.phone_number,
        "roles": role_names,
        "verified": True,
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
        "expires_in": 3600,
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

    # 3. Query UserSession record
    stmt = select(UserSession).where(UserSession.refresh_token_hash == token_hash)
    result = await db.execute(stmt)
    session_rec = result.scalar_one_or_none()

    if not session_rec:
        raise UnauthorizedException(detail="Invalid or unrecognized refresh token", code="INVALID_TOKEN")

    # 4. Token Reuse Detection
    if session_rec.is_revoked or session_rec.revoked_at is not None:
        now = datetime.now(timezone.utc)
        # REUSE DETECTED: Immediately revoke ALL active sessions for that user
        await db.execute(
            update(UserSession)
            .where(UserSession.user_id == session_rec.user_id, UserSession.is_revoked.is_(False))
            .values(is_revoked=True, revoked_at=now)
        )
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
                "all_sessions_revoked": True,
            },
            ip_address=ip_address,
        )
        await db.commit()
        raise UnauthorizedException(
            detail="Refresh token reuse detected; all sessions revoked",
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

    role_names: list[str] = [r.role.value if hasattr(r.role, "value") else str(r.role) for r in user.roles]
    token_claims = {
        "phone_number": user.phone_number,
        "roles": role_names,
        "verified": True,
    }

    # 8. Issue fresh access token and new rotating refresh token under same family_id
    family_id = session_rec.family_id or uuid.uuid4()
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
        "expires_in": 3600,
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
    user_role_names = [r.role.value if hasattr(r.role, "value") else str(r.role) for r in user.roles]

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
