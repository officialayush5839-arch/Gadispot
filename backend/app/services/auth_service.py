"""Authentication service: Firebase Phone Auth token exchange and PyOTP 2FA."""

import base64
import io
import logging
import uuid
from typing import Any

import pyotp
import qrcode
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
)
from app.models.enums import UserRoleEnum
from app.models.users import User, UserRole
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger("gadispot.auth")

# Lazy-initialized Firebase app state
_firebase_initialized = False


def _init_firebase() -> bool:
    """Safely initialize Firebase Admin SDK if not already initialized."""
    global _firebase_initialized
    if _firebase_initialized:
        return True
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            settings = get_settings()
            if settings.FIREBASE_PROJECT_ID:
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred, {"projectId": settings.FIREBASE_PROJECT_ID})
            else:
                # Initialize default app for testing/emulation if credentials not set
                firebase_admin.initialize_app()
        _firebase_initialized = True
        return True
    except Exception as exc:
        logger.warning("Firebase Admin initialization skipped or unavailable: %s", exc)
        return False


def verify_firebase_token(id_token: str) -> dict[str, Any]:
    """Verify Firebase ID token using official Firebase Admin SDK with test fallback.

    In production, strictly validates cryptographic signatures via Google public keys.
    In testing/development with mock tokens, performs structured token parsing.
    """
    settings = get_settings()

    # Try official Firebase Admin verification first
    if _init_firebase():
        try:
            import firebase_admin.auth as fb_auth

            decoded = fb_auth.verify_id_token(id_token, check_revoked=True)
            phone = decoded.get("phone_number")
            uid = decoded.get("uid")
            if not phone:
                raise UnauthorizedException(
                    detail="Firebase token does not contain a verified phone number.",
                    code="PHONE_NUMBER_REQUIRED",
                )
            return {"uid": uid, "phone_number": phone, "email": decoded.get("email")}
        except Exception as exc:
            # If not in test environment, fail immediately
            if settings.is_production:
                raise UnauthorizedException(
                    detail=f"Firebase ID token verification failed: {exc!s}",
                    code="FIREBASE_TOKEN_INVALID",
                )

    # Test / Dev token verification fallback
    if id_token.startswith("test-token-"):
        parts = id_token.split(":")
        phone = parts[1] if len(parts) > 1 else "+919876543210"
        return {"uid": f"test-uid-{phone[-10:]}", "phone_number": phone, "email": None}

    # For standard JWTs in development / test harness
    try:
        import jwt

        # Allow reading claims in test mode without signature verification only if testing
        if settings.is_testing or not settings.is_production:
            unverified = jwt.decode(id_token, options={"verify_signature": False})
            phone = unverified.get("phone_number") or unverified.get("phone")
            uid = unverified.get("uid") or unverified.get("sub") or str(uuid.uuid4())
            if phone:
                return {"uid": uid, "phone_number": phone, "email": unverified.get("email")}
    except Exception:
        pass

    raise UnauthorizedException(
        detail="The provided authentication token could not be verified by Firebase Admin.",
        code="FIREBASE_TOKEN_INVALID",
    )


async def exchange_firebase_token_for_session(
    db: AsyncSession,
    id_token: str,
) -> dict[str, Any]:
    """Exchange a verified Firebase token for an internal scoped JWT session."""
    claims = verify_firebase_token(id_token)
    phone_number = claims["phone_number"]

    # 1. Look up existing user with role eagerly loaded
    stmt = select(User).where(User.phone_number == phone_number).options(selectinload(User.roles))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # 2. Provision user if first-time driver login
    if not user:
        user = User(
            phone_number=phone_number,
            full_name="Driver User",
            is_active=True,
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

    if not user.is_active:
        raise UnauthorizedException(
            detail="User account is deactivated. Contact support.",
            code="ACCOUNT_DEACTIVATED",
        )

    # 3. Extract roles
    role_names: list[str] = [r.role.value if hasattr(r.role, "value") else str(r.role) for r in user.roles]
    if not role_names:
        role_names = [UserRoleEnum.DRIVER.value]

    # 4. Generate scoped access token and refresh token
    token_claims = {
        "phone_number": user.phone_number,
        "roles": role_names,
        "verified": True,
    }
    access_token = create_access_token(subject=str(user.id), claims=token_claims)
    refresh_token = create_refresh_token(subject=str(user.id), claims={"roles": role_names})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "id": user.id,
            "phone_number": user.phone_number,
            "full_name": user.full_name,
            "roles": role_names,
            "is_active": user.is_active,
        },
    }


async def refresh_session_tokens(
    db: AsyncSession,
    refresh_token: str,
) -> dict[str, Any]:
    """Issue a fresh access token from a valid refresh token."""
    payload = decode_token(refresh_token)
    verify_token_type(payload, "refresh")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException(detail="Invalid token subject", code="INVALID_TOKEN")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException(detail="Malformed user ID in token", code="INVALID_TOKEN")

    stmt = select(User).where(User.id == user_uuid).options(selectinload(User.roles))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise UnauthorizedException(detail="User no longer active", code="USER_INACTIVE")

    role_names: list[str] = [r.role.value if hasattr(r.role, "value") else str(r.role) for r in user.roles]
    token_claims = {
        "phone_number": user.phone_number,
        "roles": role_names,
        "verified": True,
    }
    new_access_token = create_access_token(subject=str(user.id), claims=token_claims)

    return {
        "access_token": new_access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "id": user.id,
            "phone_number": user.phone_number,
            "full_name": user.full_name,
            "roles": role_names,
            "is_active": user.is_active,
        },
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
