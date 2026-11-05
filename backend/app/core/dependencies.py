"""FastAPI async dependency injectors."""

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import async_session_factory


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


__all__ = ["Settings", "get_db", "get_redis", "get_settings"]
