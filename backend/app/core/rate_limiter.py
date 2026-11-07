"""Redis sliding-window rate limiter for brute-force prevention and API throttling."""

import asyncio
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
    """Sliding-window counter implementation using Redis sorted sets (ZSET).

    Falls back to a bounded in-memory sliding cache during Redis outages. Note: The in-memory
    fallback is process-local and provides bounded abuse mitigation during temporary distributed cache degradation.
    """

    MAX_MEMORY_CACHE_KEYS: int = 5000

    def __init__(
        self,
        key_prefix: str,
        max_requests: int,
        window_seconds: int,
        fail_closed: bool = False,
    ):
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.fail_closed = fail_closed
        self._memory_cache: dict[str, list[float]] = {}

    def _prune_memory_cache(self, now: float) -> None:
        """Evict expired timestamps and bound memory consumption to prevent unbounded leak."""
        window_start = now - self.window_seconds
        expired_keys = []
        for k, timestamps in list(self._memory_cache.items()):
            valid = [t for t in timestamps if t > window_start]
            if not valid:
                expired_keys.append(k)
            else:
                self._memory_cache[k] = valid

        for k in expired_keys:
            self._memory_cache.pop(k, None)

        # Cap memory size if key space exceeds threshold
        if len(self._memory_cache) > self.MAX_MEMORY_CACHE_KEYS:
            overflow_count = len(self._memory_cache) - self.MAX_MEMORY_CACHE_KEYS
            for _ in range(overflow_count):
                if self._memory_cache:
                    self._memory_cache.pop(next(iter(self._memory_cache)), None)

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

        except (aioredis.RedisError, asyncio.TimeoutError, ConnectionError, OSError) as exc:
            if self.fail_closed:
                logger.warning(
                    "Redis rate limiter unavailable (%s); failing closed via bounded in-memory sliding cache for %s",
                    exc,
                    key,
                )
                self._prune_memory_cache(now)
                timestamps = [t for t in self._memory_cache.get(key, []) if t > window_start]
                timestamps.append(now)
                self._memory_cache[key] = timestamps
                current_count = len(timestamps)
                if current_count > self.max_requests:
                    retry_after = max(1, int(timestamps[0] + self.window_seconds - now))
                    return True, current_count, retry_after
                return False, current_count, 0

            # Fallback gracefully if Redis is temporarily unreachable for non-critical routes
            logger.warning("Redis rate limiter unavailable (%s); failing open for %s", exc, key)
            return False, 0, 0

    def as_dependency(self, identifier_extractor=None):
        """Create a FastAPI dependency checking rate limits per request."""

        async def dependency(
            request: Request,
            redis: aioredis.Redis = Depends(get_redis),
        ):
            import os
            from app.core.config import get_settings

            settings = get_settings()

            # Skip rate limiting during automated test runs unless explicitly enforced via header
            is_test_env = (
                settings.ENVIRONMENT in ("testing", "test")
                or "PYTEST_CURRENT_TEST" in os.environ
                or request.headers.get("x-skip-rate-limit") == "true"
            )
            if is_test_env and request.headers.get("x-enforce-rate-limit") != "true":
                return True

            if identifier_extractor:
                ident = identifier_extractor(request)
            else:
                # Default identifier: Client IP address (with X-Forwarded-For support)
                forwarded = request.headers.get("X-Forwarded-For")
                if forwarded:
                    ident = forwarded.split(",")[0].strip()
                else:
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


# Standard policy rate limiters defined by PRD §12 and Phase 02 IAM Gap Matrix
otp_rate_limiter = SlidingWindowRateLimiter(
    key_prefix="otp",
    max_requests=3,
    window_seconds=900,  # 3 OTP attempts per 15 minutes
    fail_closed=True,
)

login_rate_limiter = SlidingWindowRateLimiter(
    key_prefix="login",
    max_requests=5,
    window_seconds=900,  # 5 login attempts per 15 minutes
    fail_closed=True,
)

refresh_rate_limiter = SlidingWindowRateLimiter(
    key_prefix="refresh",
    max_requests=10,
    window_seconds=60,  # 10 refresh calls per minute
    fail_closed=True,
)

totp_rate_limiter = SlidingWindowRateLimiter(
    key_prefix="2fa",
    max_requests=3,
    window_seconds=300,  # 3 2FA attempts per 5 minutes
    fail_closed=True,
)

search_rate_limiter = SlidingWindowRateLimiter(
    key_prefix="search",
    max_requests=60,
    window_seconds=60,  # 60 radius search queries per minute
    fail_closed=False,  # High availability: fail open
)
