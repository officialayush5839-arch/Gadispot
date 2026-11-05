import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException


def generate_request_id() -> str:
    """Generate a unique UUIDv4 request correlation identifier."""
    return str(uuid.uuid4())


def is_valid_uuid(val: str) -> bool:
    """Check if the provided string is a valid UUID."""
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure URL-safe random string."""
    return secrets.token_urlsafe(nbytes)


def constant_time_compare(val1: str, val2: str) -> bool:
    """Perform constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(val1.encode("utf-8"), val2.encode("utf-8"))


def create_access_token(
    subject: str,
    claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed internal access token with short TTL (default 60m)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    if claims:
        to_encode.update(claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(
    subject: str,
    claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed internal refresh token with long TTL (default 30d)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }
    if claims:
        to_encode.update(claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify an internal JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(
            detail="Token signature has expired. Please refresh your session.",
            code="TOKEN_EXPIRED",
        )
    except jwt.InvalidTokenError:
        raise UnauthorizedException(
            detail="Provided authentication token is invalid or malformed.",
            code="INVALID_TOKEN",
        )


def verify_token_type(payload: dict[str, Any], expected_type: str) -> dict[str, Any]:
    """Verify that decoded payload matches the expected token type ('access' or 'refresh')."""
    token_type = payload.get("type")
    if token_type != expected_type:
        raise UnauthorizedException(
            detail=f"Invalid token type: expected '{expected_type}', got '{token_type}'.",
            code="INVALID_TOKEN_TYPE",
        )
    return payload
