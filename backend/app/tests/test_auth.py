import jwt


async def test_verify_rejects_missing_api_key(client):
    response = await client.get("/api/v1/auth/verify")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_verify_rejects_invalid_api_key(client):
    response = await client.get(
        "/api/v1/auth/verify", headers={"Authorization": "Bearer wrong-key"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_verify_accepts_valid_api_key(client, auth_headers):
    response = await client.get("/api/v1/auth/verify", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}


async def test_token_does_not_contain_raw_api_key(client, api_key):
    response = await client.post("/api/v1/auth/token", json={"api_key": api_key})
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    decoded = jwt.decode(access_token, options={"verify_signature": False})
    assert "raw_key" not in decoded
    assert "key_type" not in decoded
    assert "api_key_id" in decoded


async def test_auth_me_sanitized(client, auth_headers):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "raw_key" not in data
    assert "api_key_id" in data
    assert "name" in data


async def test_demo_key_endpoint_removed(client):
    response = await client.post("/api/v1/auth/demo-key")
    assert response.status_code == 404
