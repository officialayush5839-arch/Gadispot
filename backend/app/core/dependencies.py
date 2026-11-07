"""FastAPI async dependency injectors."""

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token, verify_token_type
from app.db.session import async_session_factory
from app.models.revoked_token import RevokedToken
from app.models.session import UserSession
from app.models.users import AccountStatus, User

logger = logging.getLogger("gadispot.dependencies")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency yielding an async SQLAlchemy session with transaction isolation."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_redis(request: Request) -> AsyncGenerator[aioredis.Redis, None]:
    """Dependency providing access to the shared application Redis client."""
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is not None:
        yield redis_client
    else:
        # Fallback for isolated test execution where lifespan did not run
        settings = get_settings()
        client = aioredis.from_url(
            settings.REDIS_URL,
            protocol=settings.REDIS_PROTOCOL,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
        )
        try:
            yield client
        finally:
            await client.aclose()


async def get_current_user(
    request: Request,
    authorization: str | None = Header(None, description="Bearer access token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency extracting, validating, and hydrating authenticated user with account lifecycle checks."""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException(
            detail="Missing or malformed Authorization header. Bearer token required.",
            code="MISSING_BEARER_TOKEN",
        )

    raw_token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(raw_token)
    verify_token_type(payload, "access")

    # Redis token blocklist verification with authoritative database fallback
    jti = payload.get("jti")
    family_id = payload.get("family_id")
    redis_failed = False

    if jti:
        redis_client = None
        app = getattr(request, "app", None)
        if app is not None and hasattr(app, "state"):
            redis_client = getattr(app.state, "redis", None)
        elif hasattr(request, "state"):
            redis_client = getattr(request.state, "redis", None)

        created_client = False
        if redis_client is None and app is not None:
            try:
                settings = get_settings()
                redis_client = aioredis.from_url(
                    settings.REDIS_URL,
                    protocol=settings.REDIS_PROTOCOL,
                    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                )
                created_client = True
            except Exception:
                redis_client = None
                redis_failed = True

        if redis_client is not None:
            try:
                is_blocked = await redis_client.get(f"jwt:blocklist:{jti}")
                if is_blocked:
                    raise UnauthorizedException(
                        detail="Token has been revoked",
                        code="TOKEN_REVOKED",
                    )
                if family_id:
                    is_family_revoked = await redis_client.get(f"jwt:family:revoked:{family_id}")
                    if is_family_revoked:
                        raise UnauthorizedException(
                            detail="Session family has been revoked.",
                            code="TOKEN_REVOKED",
                        )
            except UnauthorizedException:
                raise
            except (aioredis.RedisError, asyncio.TimeoutError, ConnectionError, OSError) as r_exc:
                logger.warning(
                    "Redis blocklist check failed (%s); falling back to authoritative database check",
                    r_exc,
                )
                redis_failed = True
            finally:
                if created_client:
                    await redis_client.aclose()
        else:
            redis_failed = True

    # Authoritative Database Fallback:
    # If Redis is unavailable or failed, verify the token's individual JTI and session family revocation in PostgreSQL.
    if redis_failed:
        try:
            # 1. Check individual JTI revocation in persistent table
            if jti:
                jti_stmt = select(RevokedToken.jti).where(RevokedToken.jti == jti).limit(1)
                jti_res = await db.execute(jti_stmt)
                if jti_res.scalar_one_or_none() is not None:
                    raise UnauthorizedException(
                        detail="Token has been revoked",
                        code="TOKEN_REVOKED",
                    )

            # 2. Check session family revocation if family_id is present
            if family_id:
                fam_uuid = uuid.UUID(family_id)
                active_session_stmt = (
                    select(UserSession.id)
                    .where(
                        UserSession.family_id == fam_uuid,
                        UserSession.is_revoked.is_(False),
                        UserSession.expires_at > datetime.now(timezone.utc),
                    )
                    .limit(1)
                )
                active_res = await db.execute(active_session_stmt)
                if active_res.scalar_one_or_none() is None:
                    raise UnauthorizedException(
                        detail="Token family has been revoked or expired.",
                        code="TOKEN_REVOKED",
                    )
        except UnauthorizedException:
            raise
        except Exception as db_exc:
            logger.error("Authoritative database session verification failed: %s", db_exc)
            raise UnauthorizedException(
                detail="Unable to verify token revocation status.",
                code="REVOCATION_CHECK_UNAVAILABLE",
            )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException(detail="Token subject missing", code="INVALID_TOKEN")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException(detail="Malformed UUID in token subject", code="INVALID_TOKEN")

    # Fetch user from database with roles eagerly loaded
    stmt = select(User).where(User.id == user_uuid).options(selectinload(User.roles))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException(detail="User no longer exists", code="USER_NOT_FOUND")

    # Account lifecycle & status enforcement
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

    # Attach user to request state for downstream logging/telemetry
    request.state.user = user
    return user


async def get_current_user_optional(
    request: Request,
    authorization: str | None = Header(None, description="Bearer access token"),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Optional user extractor for endpoints that support both authenticated and unauthenticated callers."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return await get_current_user(request=request, authorization=authorization, db=db)
    except Exception:
        return None


__all__ = [
    "Settings",
    "get_current_user",
    "get_current_user_optional",
    "get_db",
    "get_redis",
    "get_settings",
]
