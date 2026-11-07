"""Authentication and 2FA endpoints."""

import redis.asyncio as aioredis
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_redis
from app.core.rate_limiter import (
    login_rate_limiter,
    refresh_rate_limiter,
    totp_rate_limiter,
)
from app.core.security import decode_token, decrypt_totp_secret, encrypt_totp_secret
from app.models.users import User
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.schemas.auth import (
    FirebaseExchangeRequest,
    LogoutRequest,
    LogoutResponse,
    MfaChallengeRequest,
    RefreshTokenRequest,
    SwitchRoleRequest,
    SwitchRoleResponse,
    TokenResponse,
    TotpSetupRequest,
    TotpSetupResponse,
    TotpVerifyRequest,
    TotpVerifyResponse,
    UserProfileResponse,
)
from app.services.auth_service import (
    exchange_firebase_token_for_session,
    generate_totp_qr_base64,
    generate_totp_secret,
    get_permissions_for_roles,
    get_totp_provisioning_uri,
    logout_user_session,
    refresh_session_tokens,
    switch_user_role,
    verify_mfa_challenge,
    verify_totp_code,
)

router = APIRouter()


@router.post(
    "/exchange",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange Firebase ID token for internal scoped JWT session",
    responses={
        200: {"description": "Successfully exchanged token and established session", "model": TokenResponse},
        401: {"description": "Invalid, expired, or unverified Firebase ID token"},
        403: {"description": "Account suspended, disabled, or inactive"},
        422: {"description": "Validation error in request payload"},
    },
    dependencies=[Depends(login_rate_limiter.as_dependency())],
)
@router.post(
    "/session",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange Firebase ID token for internal scoped JWT session (session route alias)",
    responses={
        200: {"description": "Successfully exchanged token and established session", "model": TokenResponse},
        401: {"description": "Invalid, expired, or unverified Firebase ID token"},
        403: {"description": "Account suspended, disabled, or inactive"},
        422: {"description": "Validation error in request payload"},
    },
    dependencies=[Depends(login_rate_limiter.as_dependency())],
    include_in_schema=False,
)
@router.post(
    "/firebase-exchange",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange Firebase ID token (mobile route alias)",
    responses={
        200: {"description": "Successfully exchanged token and established session", "model": TokenResponse},
        401: {"description": "Invalid, expired, or unverified Firebase ID token"},
        403: {"description": "Account suspended, disabled, or inactive"},
        422: {"description": "Validation error in request payload"},
    },
    dependencies=[Depends(login_rate_limiter.as_dependency())],
    include_in_schema=False,
)
async def exchange_token(
    payload: FirebaseExchangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Validate a verified Firebase Phone Auth ID token and issue internal access/refresh JWTs."""
    ip_addr = request.client.host if request.client else None
    device_info = payload.device_info or request.headers.get("User-Agent")
    session_data = await exchange_firebase_token_for_session(
        db=db,
        id_token=payload.id_token,
        ip_address=ip_addr,
        device_info=device_info,
        totp_code=payload.totp_code,
    )
    return TokenResponse(**session_data)


# Backward-compatible function alias for existing internal references
create_session = exchange_token


@router.post(
    "/2fa/challenge",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete two-factor authentication challenge to issue session tokens",
    dependencies=[Depends(totp_rate_limiter.as_dependency())],
)
async def challenge_totp(
    payload: MfaChallengeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    """Verify MFA challenge token and TOTP code to establish an authenticated session."""
    ip_addr = request.client.host if request.client else None
    device_info = payload.device_info or request.headers.get("User-Agent")
    session_data = await verify_mfa_challenge(
        db=db,
        mfa_token=payload.mfa_token,
        totp_code=payload.totp_code,
        redis=redis,
        ip_address=ip_addr,
        device_info=device_info,
    )
    return TokenResponse(**session_data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh internal session access token with single-use rotation and reuse detection",
    responses={
        200: {"description": "Successfully rotated refresh token and issued fresh token pair", "model": TokenResponse},
        401: {"description": "Invalid, expired, or compromised/replayed refresh token"},
        403: {"description": "Account suspended, disabled, or inactive"},
        422: {"description": "Validation error in request payload"},
    },
    dependencies=[Depends(refresh_rate_limiter.as_dependency())],
)
async def refresh_session(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    """Issue fresh access token and rotating refresh token using a valid, non-revoked refresh token."""
    ip_addr = request.client.host if request.client else None
    session_data = await refresh_session_tokens(
        db=db,
        refresh_token=payload.refresh_token,
        redis=redis,
        ip_address=ip_addr,
    )
    return TokenResponse(**session_data)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Terminate active session, revoke refresh token, and blocklist access JWT",
    responses={
        200: {"description": "Successfully logged out and revoked session", "model": LogoutResponse},
        401: {"description": "Unauthenticated or revoked access token"},
        403: {"description": "Account suspended or deactivated"},
    },
)
async def logout(
    request: Request,
    payload: LogoutRequest | None = None,
    authorization: str | None = Header(None, description="Bearer access token"),
    x_refresh_token: str | None = Header(None, alias="X-Refresh-Token", description="Optional refresh token in header"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> LogoutResponse:
    """Revoke session and refresh token in database, blacklisting access token JTI in Redis."""
    jti: str | None = None
    ttl: int = 3600
    if authorization and authorization.startswith("Bearer "):
        try:
            token_str = authorization.split(" ", 1)[1].strip()
            decoded = decode_token(token_str)
            jti = decoded.get("jti")
            exp = decoded.get("exp")
            if exp:
                now_ts = datetime.now(timezone.utc).timestamp()
                ttl = max(1, int(exp - now_ts))
        except Exception:
            pass

    ip_addr = request.client.host if request.client else None
    refresh_tok = (payload.refresh_token if payload else None) or x_refresh_token

    await logout_user_session(
        db=db,
        user=current_user,
        access_token_jti=jti,
        access_token_ttl=ttl,
        refresh_token=refresh_tok,
        redis=redis,
        ip_address=ip_addr,
    )
    return LogoutResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve authenticated principal's profile, roles, and status",
    responses={
        200: {"description": "User profile retrieved successfully", "model": UserProfileResponse},
        401: {"description": "Missing, invalid, or revoked access token"},
        403: {"description": "Account suspended or deactivated"},
    },
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """Return the profile, role assignments, lifecycle status, and granular permissions of the authenticated caller."""
    role_names = current_user.role_names
    permissions = get_permissions_for_roles(role_names)
    return UserProfileResponse(
        id=current_user.id,
        phone_number=current_user.phone_number,
        full_name=current_user.full_name,
        email=current_user.email,
        roles=role_names,
        status=current_user.status.value if hasattr(current_user.status, "value") else str(current_user.status),
        is_active=current_user.is_active,
        permissions=permissions,
        firebase_uid=current_user.firebase_uid,
    )


@router.post(
    "/switch-role",
    response_model=SwitchRoleResponse,
    status_code=status.HTTP_200_OK,
    summary="Switch active viewport role for multi-role users (e.g. Driver <-> Space Owner)",
)
async def switch_active_role(
    payload: SwitchRoleRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SwitchRoleResponse:
    """Validate user possesses the requested role and switch active viewport."""
    ip_addr = request.client.host if request.client else None
    result = await switch_user_role(
        db=db,
        user=current_user,
        target_role=payload.target_role,
        ip_address=ip_addr,
    )
    return SwitchRoleResponse(**result)


@router.post(
    "/2fa/setup",
    response_model=TotpSetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Initialize or re-enroll RFC 6238 TOTP 2FA for authenticated principal",
)
async def setup_totp_2fa(
    payload: TotpSetupRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TotpSetupResponse:
    """Generate high-entropy Base32 secret, persist encrypted in database, and return provisioning QR code."""
    secret = generate_totp_secret()
    label = current_user.email or current_user.phone_number
    uri = get_totp_provisioning_uri(secret, label)
    qr_b64 = generate_totp_qr_base64(uri)

    # Protect re-enrollment: if 2FA is already active, require current 2FA code verification
    # and store new secret in totp_pending_secret_encrypted without disabling active 2FA!
    if getattr(current_user, "totp_enabled", False):
        current_code = payload.current_totp_code if payload else None
        if not current_code:
            raise ForbiddenException(
                detail="Valid current 2FA verification code required to authorize re-enrollment.",
                code="MFA_VERIFICATION_REQUIRED",
            )
        try:
            curr_secret = decrypt_totp_secret(current_user.totp_secret_encrypted)
        except Exception:
            raise UnauthorizedException(
                detail="Failed to decrypt enrolled TOTP credentials.",
                code="TOTP_DECRYPT_ERROR",
            )
        if not verify_totp_code(curr_secret, current_code):
            raise UnauthorizedException(
                detail="Current two-factor authentication code is invalid.",
                code="INVALID_TOTP_CODE",
            )

        # Store in pending column; active factor remains enabled and untouched!
        current_user.totp_pending_secret_encrypted = encrypt_totp_secret(secret)
    else:
        # Initial enrollment: store pending initial secret
        current_user.totp_secret_encrypted = encrypt_totp_secret(secret)
        current_user.totp_enabled = False
        current_user.totp_verified_at = None

    await db.flush()

    return TotpSetupResponse(
        secret=secret,
        provisioning_uri=uri,
        qr_code_base64=qr_b64,
    )


@router.post(
    "/2fa/verify",
    response_model=TotpVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify an RFC 6238 6-digit TOTP code against the authenticated account's secret",
    dependencies=[Depends(totp_rate_limiter.as_dependency())],
)
async def verify_totp(
    payload: TotpVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TotpVerifyResponse:
    """Verify code strictly against the caller's account-persisted encrypted secret. Activates 2FA upon success."""
    from datetime import datetime, timezone

    # Determine whether verifying re-enrollment or initial setup
    is_re_enrollment = bool(getattr(current_user, "totp_pending_secret_encrypted", None))
    secret_encrypted = (
        current_user.totp_pending_secret_encrypted if is_re_enrollment else current_user.totp_secret_encrypted
    )

    if not secret_encrypted:
        return TotpVerifyResponse(
            valid=False,
            message="TOTP 2FA enrollment has not been initialized. Please call /2fa/setup first.",
        )

    try:
        authoritative_secret = decrypt_totp_secret(secret_encrypted)
    except Exception:
        return TotpVerifyResponse(
            valid=False,
            message="Internal error decrypting enrolled TOTP credentials.",
        )

    is_valid = verify_totp_code(authoritative_secret, payload.code)
    if is_valid:
        if is_re_enrollment:
            current_user.totp_secret_encrypted = current_user.totp_pending_secret_encrypted
            current_user.totp_pending_secret_encrypted = None
        current_user.totp_enabled = True
        current_user.totp_verified_at = datetime.now(timezone.utc)
        await db.flush()

    return TotpVerifyResponse(
        valid=is_valid,
        message="Verification successful. Two-factor authentication is active."
        if is_valid
        else "Invalid or expired verification code",
    )
