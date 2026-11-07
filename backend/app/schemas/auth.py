"""Pydantic schemas for authentication, session tokens, and TOTP 2FA."""

import uuid

from pydantic import BaseModel, Field


class FirebaseExchangeRequest(BaseModel):
    """Payload to exchange a verified Firebase Phone Auth ID token for internal application tokens."""

    id_token: str = Field(..., min_length=10, description="Verified Firebase Phone Auth ID token")
    fcm_token: str | None = Field(None, description="Optional FCM device push token for notifications")
    device_info: str | None = Field(None, description="Optional client device info / metadata")


FirebaseSessionRequest = FirebaseExchangeRequest


class RefreshTokenRequest(BaseModel):
    """Payload to refresh an existing access token using a refresh token."""

    refresh_token: str = Field(..., min_length=10, description="Valid internal refresh token")


class UserSummary(BaseModel):
    """Summary of user profile, role assignments, and permissions."""

    id: uuid.UUID
    phone_number: str
    full_name: str
    roles: list[str]
    is_active: bool
    status: str = "ACTIVE"
    email: str | None = None
    firebase_uid: str | None = None
    permissions: list[str] = Field(
        default_factory=list, description="Derived granular permissions for the user's roles"
    )


class UserProfileResponse(BaseModel):
    """Authenticated user profile returned by GET /api/v1/auth/me."""

    id: uuid.UUID
    phone_number: str
    full_name: str
    email: str | None = None
    roles: list[str]
    status: str = "ACTIVE"
    is_active: bool
    permissions: list[str] = Field(
        default_factory=list, description="Derived granular permissions for the user's roles"
    )
    firebase_uid: str | None = None


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


class LogoutRequest(BaseModel):
    """Optional payload when logging out to explicitly revoke refresh token."""

    refresh_token: str | None = Field(None, description="Optional refresh token to invalidate")


class LogoutResponse(BaseModel):
    """Response returned upon session logout."""

    message: str = Field("Successfully logged out", description="Confirmation message")


class SwitchRoleRequest(BaseModel):
    """Payload to switch active role viewport for dual-role accounts."""

    target_role: str = Field(..., min_length=2, max_length=32, description="Target role (e.g. DRIVER, SPACE_OWNER)")


class SwitchRoleResponse(BaseModel):
    """Response returned after switching active role viewport."""

    active_role: str = Field(..., description="The new active role")
    allowed_roles: list[str] = Field(default_factory=list, description="All allowed roles for the user")
    message: str = Field(..., description="Confirmation message")
