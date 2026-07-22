import uuid

import pytest
from httpx import AsyncClient

from app.core.config import get_settings

pytestmark = pytest.mark.anyio


async def test_rate_limiting_middleware(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Temporarily lower the rate limit for this test
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "10")
    get_settings.cache_clear()

    try:
        endpoint = "/api/v1/auth/me"
        unique_ip = f"192.168.1.{uuid.uuid4().int % 255}"
        headers = {"X-Forwarded-For": unique_ip}

        # Send 11 requests (rate limit is 10)
        for i in range(11):
            response = await client.get(endpoint, headers=headers)
            if i < 10:
                assert response.status_code == 401, (
                    f"Request {i + 1} failed with {response.status_code}"
                )
                assert "X-RateLimit-Remaining" in response.headers
            else:
                assert response.status_code == 429
                assert response.json()["detail"] == "Too many requests, please try again later."
                assert "X-RateLimit-Remaining" in response.headers
                assert response.headers["X-RateLimit-Remaining"] == "0"
    finally:
        # Restore cache for other tests
        get_settings.cache_clear()


async def test_security_headers_present(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "default-src 'self'" in response.headers.get("Content-Security-Policy", "")


async def test_rate_limiting_fallback_when_redis_fails(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "3")
    get_settings.cache_clear()

    from app.queue import redis_client

    def mock_broken_redis():
        raise RuntimeError("Redis connection broken")

    monkeypatch.setattr(redis_client, "get_redis", mock_broken_redis)

    try:
        unique_ip = f"10.200.1.{uuid.uuid4().int % 255}"
        headers = {"X-Forwarded-For": unique_ip}
        for i in range(4):
            response = await client.post("/api/v1/workflows", headers=headers, json={})
            if i < 3:
                assert response.status_code != 429
            else:
                assert response.status_code == 429
                assert response.json()["detail"] == "Too many requests, please try again later."
    finally:
        get_settings.cache_clear()


async def test_health_and_metrics_polling_exempt_from_rate_limit(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "2")
    get_settings.cache_clear()

    try:
        unique_ip = f"10.201.1.{uuid.uuid4().int % 255}"
        headers = {"X-Forwarded-For": unique_ip}
        for _ in range(5):
            response = await client.get("/health/live", headers=headers)
            assert response.status_code == 200
    finally:
        get_settings.cache_clear()
