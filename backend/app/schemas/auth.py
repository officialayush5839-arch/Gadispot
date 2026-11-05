"""Pydantic schemas for authentication, session tokens, and TOTP 2FA."""

import uuid

from pydantic import BaseModel, Field


class FirebaseSessionRequest(BaseModel):
    """Payload to exchange a verified Firebase ID token for internal JWT tokens."""

    id_token: str = Field(..., min_length=10, description="Verified Firebase Phone Auth ID token")
    fcm_token: str | None = Field(None, description="Optional FCM device push token for notifications")


class RefreshTokenRequest(BaseModel):
    """Payload to refresh an existing access token using a refresh token."""

    refresh_token: str = Field(..., min_length=10, description="Valid internal refresh token")


class UserSummary(BaseModel):
    """Summary of user profile and role assignments."""

    id: uuid.UUID
    phone_number: str
    full_name: str
    roles: list[str]
    is_active: bool


class TokenResponse(BaseModel):
    """Session token pair returned upon successful authentication."""

    access_token: str = Field(..., description="Scoped JWT access token (60m validity)")
    refresh_token: str = Field(..., description="Internal refresh token (30d validity)")
    token_type: str = Field("bearer", description="Token authentication scheme")
    expires_in: int = Field(3600, description="Access token expiry in seconds")
    user: UserSummary


class TotpSetupResponse(BaseModel):
    """Provisioning details for RFC 6238 TOTP 2FA."""

    secret: str = Field(..., description="Base32 TOTP shared secret")
    provisioning_uri: str = Field(..., description="Standard otpauth:// URI for authenticator apps")
    qr_code_base64: str = Field(..., description="Data URL (base64 PNG) of the authenticator QR code")


class TotpVerifyRequest(BaseModel):
    """Payload to verify an RFC 6238 6-digit TOTP code."""

    secret: str = Field(..., min_length=16, description="Base32 TOTP secret")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP verification code")


class TotpVerifyResponse(BaseModel):
    """Result of TOTP code verification."""

    valid: bool = Field(..., description="Whether the TOTP code was valid within drift window")
    message: str = Field(..., description="Status message")
