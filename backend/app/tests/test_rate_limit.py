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
                    f"Request {i+1} failed with {response.status_code}"
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
