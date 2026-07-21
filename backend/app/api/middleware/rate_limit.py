import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class InMemoryFallbackRateLimiter:
    """Thread-safe sliding window fallback rate limiter used if Redis is unreachable."""

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, identifier: str, limit: int, window: int) -> tuple[bool, int]:
        async with self._lock:
            now = time.time()
            cutoff = now - window
            timestamps = [t for t in self._requests[identifier] if t > cutoff]
            timestamps.append(now)
            self._requests[identifier] = timestamps

            count = len(timestamps)
            allowed = count <= limit
            remaining = max(0, limit - count)
            return allowed, remaining


_in_memory_limiter = InMemoryFallbackRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Only rate limit the /api routes
        if not path.startswith("/api/"):
            return await call_next(request)

        # H-3: Restrict rate limit exclusions to GET read/health endpoints only
        if request.method == "GET" and (
            path in ("/api/v1/metrics/summary", "/health/live", "/health/ready")
            or path.startswith("/health/")
        ):
            return await call_next(request)

        # Get client identifier
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        api_key = request.headers.get(get_settings().api_key_header_name)
        identifier = api_key if api_key else client_ip

        settings = get_settings()
        limit = settings.rate_limit_requests
        window = settings.rate_limit_window_seconds

        # Import locally to avoid circular imports during app initialization
        from app.queue.redis_client import get_redis

        try:
            redis: Redis = get_redis()
            key = f"rate_limit:{identifier}"

            async with redis.pipeline() as pipe:
                pipe.incr(key)
                pipe.expire(key, window, nx=True)
                results = await pipe.execute()

            request_count = results[0]

            if request_count > limit:
                logger.warning("Rate limit exceeded for %s", identifier)
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests, please try again later."},
                )
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(window)
                return response

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - request_count))
            return response

        except Exception as e:
            # H-2: Fallback to in-memory sliding window limiter if Redis is down
            logger.warning("Redis rate limiter unavailable (%s), using in-memory fallback", e)
            allowed, remaining = await _in_memory_limiter.is_allowed(identifier, limit, window)

            if not allowed:
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests, please try again later."},
                )
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(window)
                return response

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response
