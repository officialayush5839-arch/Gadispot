"""Firebase Admin SDK integration for server-side ID token verification and credential management."""

import logging
import os
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException

logger = logging.getLogger("gadispot.firebase")

_firebase_initialized = False


def init_firebase() -> bool:
    """Safely initialize Firebase Admin SDK using configured credentials or environment defaults."""
    global _firebase_initialized
    if _firebase_initialized:
        return True

    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            settings = get_settings()
            cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None) or os.getenv("FIREBASE_CREDENTIALS_PATH")

            if cred_path and os.path.isfile(cred_path):
                logger.info("Initializing Firebase Admin with certificate from: %s", cred_path)
                cred = credentials.Certificate(cred_path)
                options: dict[str, Any] = {}
                if settings.FIREBASE_PROJECT_ID:
                    options["projectId"] = settings.FIREBASE_PROJECT_ID
                firebase_admin.initialize_app(cred, options or None)
            elif settings.FIREBASE_PROJECT_ID:
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred, {"projectId": settings.FIREBASE_PROJECT_ID})
            else:
                # Fallback default initialization for development / test
                firebase_admin.initialize_app()

        _firebase_initialized = True
        return True
    except Exception as exc:
        logger.warning("Firebase Admin initialization failed or unavailable: %s", exc)
        return False


def reset_firebase_state() -> None:
    """Reset initialization state (used in testing)."""
    global _firebase_initialized
    _firebase_initialized = False


def verify_firebase_id_token(id_token: str) -> dict[str, Any]:
    """Verify Firebase ID token server-side using Firebase Admin SDK.

    In production:
    - Strictly rejects mock tokens.
    - Strictly verifies cryptographic signature against Google public keys.
    - Extracts verified phone_number and uid claims.

    In development / test:
    - Permits mock token exchange (`test-token-*`) when testing or live credentials are absent.
    - Never accepts unverified client JWT claims without signature in production.
    """
    settings = get_settings()

    if not id_token or not id_token.strip():
        raise UnauthorizedException(
            detail="Authentication token cannot be empty.",
            code="FIREBASE_TOKEN_INVALID",
        )

    # 1. Handle mock tokens in test/dev environment
    if id_token.startswith("test-token-"):
        if settings.is_production:
            logger.error("Security violation: mock Firebase token presented in production environment.")
            raise UnauthorizedException(
                detail="Mock authentication tokens are strictly forbidden in production.",
                code="FIREBASE_TOKEN_INVALID",
            )
        parts = id_token.split(":")
        phone = parts[1] if len(parts) > 1 else "+919876543210"
        uid = f"test-uid-{phone[-10:]}"
        return {"uid": uid, "phone_number": phone, "email": None}

    # 2. Server-side verification via Firebase Admin SDK
    if init_firebase():
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
        except UnauthorizedException:
            raise
        except Exception as exc:
            logger.warning("Firebase Admin token verification failed: %s", exc)
            if settings.is_production:
                raise UnauthorizedException(
                    detail="The provided authentication token is invalid or expired.",
                    code="FIREBASE_TOKEN_INVALID",
                )

    # In production or when verification fails, reject unverified client claims
    raise UnauthorizedException(
        detail="The provided authentication token could not be verified by Firebase Admin.",
        code="FIREBASE_TOKEN_INVALID",
    )
