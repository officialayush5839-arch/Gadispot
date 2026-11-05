"""Redis sliding-window rate limiter for brute-force prevention and API throttling."""

import logging
import time

import redis.asyncio as aioredis
from fastapi import Depends, Request

from app.core.dependencies import get_redis
from app.core.exceptions import DomainException

logger = logging.getLogger("gadispot.ratelimit")


class RateLimitExceededException(DomainException):
    """Raised when request volume exceeds defined policy thresholds (429 Too Many Requests)."""

    def __init__(
        self,
        detail: str = "Rate limit exceeded. Please wait before retrying.",
        retry_after: int = 60,
        code: str = "RATE_LIMIT_EXCEEDED",
    ):
        super().__init__(
            detail=detail,
            title="Too Many Requests",
            status_code=429,
            code=code,
            extra={"retry_after_seconds": retry_after},
        )
        self.retry_after = retry_after


class SlidingWindowRateLimiter:
    """Sliding-window counter implementation using Redis sorted sets (ZSET)."""

    def __init__(self, key_prefix: str, max_requests: int, window_seconds: int):
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def is_rate_limited(
        self,
        identifier: str,
        redis: aioredis.Redis,
    ) -> tuple[bool, int, int]:
        """Evaluate sliding window. Returns (is_limited, current_count, retry_after_seconds)."""
        now = time.time()
        window_start = now - self.window_seconds
        key = f"ratelimit:{self.key_prefix}:{identifier}"

        try:
            pipe = redis.pipeline()
            # 1. Remove expired timestamps older than sliding window
            pipe.zremrangebyscore(key, 0, window_start)
            # 2. Add current request timestamp
            pipe.zadd(key, {f"{now}:{time.time_ns()}": now})
            # 3. Count total active requests in window
            pipe.zcard(key)
            # 4. Refresh TTL on key
            pipe.expire(key, self.window_seconds + 5)
            results = await pipe.execute()

            current_count = results[2]
            if current_count > self.max_requests:
                # Find oldest entry in active window to compute exact Retry-After
                oldest_entries = await redis.zrange(key, 0, 0, withscores=True)
                retry_after = self.window_seconds
                if oldest_entries:
                    oldest_ts = oldest_entries[0][1]
                    retry_after = max(1, int(oldest_ts + self.window_seconds - now))
                return True, current_count, retry_after

            return False, current_count, 0

        except Exception as exc:
            # Fallback gracefully if Redis is temporarily unreachable
            logger.warning("Redis rate limiter unavailable (%s); failing open for %s", exc, key)
            return False, 0, 0

    def as_dependency(self, identifier_extractor=None):
        """Create a FastAPI dependency checking rate limits per request."""

        async def dependency(
            request: Request,
            redis: aioredis.Redis = Depends(get_redis),
        ):
            if identifier_extractor:
                ident = identifier_extractor(request)
            else:
                # Default identifier: Client IP address
                ident = request.client.host if request.client else "127.0.0.1"

            is_limited, count, retry_after = await self.is_rate_limited(ident, redis)
            if is_limited:
                logger.warning(
                    "Rate limit exceeded for %s on %s: %d/%d requests",
                    ident,
                    self.key_prefix,
                    count,
                    self.max_requests,
                )
                raise RateLimitExceededException(
                    detail=f"Rate limit of {self.max_requests} requests per {self.window_seconds}s exceeded.",
                    retry_after=retry_after,
                )
            return True

        return dependency


# Standard policy rate limiters defined by PRD §12
otp_rate_limiter = SlidingWindowRateLimiter(
    key_prefix="otp",
    max_requests=3,
    window_seconds=900,  # 3 OTP attempts per 15 minutes
)

login_rate_limiter = SlidingWindowRateLimiter(
    key_prefix="login",
    max_requests=5,
    window_seconds=900,  # 5 login attempts per 15 minutes
)

search_rate_limiter = SlidingWindowRateLimiter(
    key_prefix="search",
    max_requests=60,
    window_seconds=60,  # 60 radius search queries per minute
)
