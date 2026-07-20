async def test_verify_rejects_missing_api_key(client):
    response = await client.get("/api/v1/auth/verify")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_verify_rejects_invalid_api_key(client):
    response = await client.get("/api/v1/auth/verify", headers={"Authorization": "Bearer wrong-key"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_verify_accepts_valid_api_key(client, auth_headers):
    response = await client.get("/api/v1/auth/verify", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
