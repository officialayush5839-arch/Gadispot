"""Authentication and 2FA endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.auth import (
    FirebaseSessionRequest,
    RefreshTokenRequest,
    TokenResponse,
    TotpSetupResponse,
    TotpVerifyRequest,
    TotpVerifyResponse,
)
from app.services.auth_service import (
    exchange_firebase_token_for_session,
    generate_totp_qr_base64,
    generate_totp_secret,
    get_totp_provisioning_uri,
    refresh_session_tokens,
    verify_totp_code,
)

router = APIRouter()


@router.post(
    "/session",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange Firebase ID token for internal scoped JWT session",
)
async def create_session(
    payload: FirebaseSessionRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Validate a verified Firebase Phone Auth ID token and issue internal access/refresh JWTs."""
    session_data = await exchange_firebase_token_for_session(db, payload.id_token)
    return TokenResponse(**session_data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh internal session access token",
)
async def refresh_session(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Issue a fresh access token using a valid, non-expired internal refresh token."""
    session_data = await refresh_session_tokens(db, payload.refresh_token)
    return TokenResponse(**session_data)


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
)
async def verify_totp(payload: TotpVerifyRequest) -> TotpVerifyResponse:
    """Verify an RFC 6238 TOTP code against the shared secret within a +/- 30s clock drift window."""
    is_valid = verify_totp_code(payload.secret, payload.code)
    return TotpVerifyResponse(
        valid=is_valid,
        message="Verification successful" if is_valid else "Invalid or expired verification code",
    )
