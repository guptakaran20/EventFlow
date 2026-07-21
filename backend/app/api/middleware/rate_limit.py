import logging
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only rate limit the /api routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Exclude high-frequency polling APIs and main dashboard read paths from rate limiting
        excluded_paths = [
            "/api/v1/metrics",
            "/api/v1/health",
            "/api/v1/executions",
            "/api/v1/workflows",
            "/api/v1/observability"
        ]
        if any(request.url.path.startswith(path) for path in excluded_paths):
            return await call_next(request)

        # Get client IP (support proxies like Nginx/Cloudflare)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # You can optionally include the API Key in the rate limit key if authenticated
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

            # Atomic increment and expire using pipeline
            async with redis.pipeline() as pipe:
                pipe.incr(key)
                pipe.expire(key, window, nx=True)
                results = await pipe.execute()
                
            request_count = results[0]

            if request_count > limit:
                logger.warning(f"Rate limit exceeded for {identifier}")
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests, please try again later."}
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
            # Fallback in case Redis goes down, to avoid breaking the API
            logger.error(f"Rate limiter error: {e}")
            return await call_next(request)
