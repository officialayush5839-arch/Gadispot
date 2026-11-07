"""Authentication and 2FA endpoints."""

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_redis
from app.core.rate_limiter import (
    login_rate_limiter,
    refresh_rate_limiter,
    totp_rate_limiter,
)
from app.core.security import decode_token
from app.models.users import User
from app.schemas.auth import (
    FirebaseExchangeRequest,
    FirebaseSessionRequest,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    SwitchRoleRequest,
    SwitchRoleResponse,
    TokenResponse,
    TotpSetupResponse,
    TotpVerifyRequest,
    TotpVerifyResponse,
    UserProfileResponse,
    UserSummary,
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
    )
    return TokenResponse(**session_data)


# Backward-compatible function alias for existing internal references
create_session = exchange_token


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
                from datetime import datetime, timezone

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
    role_names = [r.role.value if hasattr(r.role, "value") else str(r.role) for r in current_user.roles]
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
    summary="Initialize RFC 6238 TOTP 2FA for operations personnel",
)
async def setup_totp_2fa() -> TotpSetupResponse:
    """Generate high-entropy Base32 secret, provisioning URI, and QR code for Google Authenticator."""
    secret = generate_totp_secret()
    uri = get_totp_provisioning_uri(secret, "operations.user@gadispot.in")
    qr_b64 = generate_totp_qr_base64(uri)
    return TotpSetupResponse(
        secret=secret,
        provisioning_uri=uri,
        qr_code_base64=qr_b64,
    )


@router.post(
    "/2fa/verify",
    response_model=TotpVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify an RFC 6238 6-digit TOTP code",
    dependencies=[Depends(totp_rate_limiter.as_dependency())],
)
async def verify_totp(payload: TotpVerifyRequest) -> TotpVerifyResponse:
    """Verify an RFC 6238 TOTP code against the shared secret within a +/- 30s clock drift window."""
    is_valid = verify_totp_code(payload.secret, payload.code)
    return TotpVerifyResponse(
        valid=is_valid,
        message="Verification successful" if is_valid else "Invalid or expired verification code",
    )
