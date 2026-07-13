async def test_live_returns_ok(client):
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_returns_dependency_status(client):
    response = await client.get("/health/ready")
    assert response.status_code in (200, 503)
    body = response.json()
    assert "database" in body
    assert "redis" in body
