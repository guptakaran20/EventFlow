from app.core.config import get_settings


async def test_verify_rejects_missing_api_key(client):
    response = await client.get("/auth/verify")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "missing_api_key"


async def test_verify_rejects_invalid_api_key(client):
    response = await client.get("/auth/verify", headers={"X-EventFlow-API-Key": "wrong-key"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


async def test_verify_accepts_valid_bootstrap_api_key(client):
    valid_key = get_settings().bootstrap_api_keys_list
    if not valid_key:
        return
    response = await client.get("/auth/verify", headers={"X-EventFlow-API-Key": valid_key[0]})
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
