import pytest
from httpx import AsyncClient


@pytest.fixture
async def other_auth_headers(client, db_session):
    from app.services.api_key_service import APIKeyService

    service = APIKeyService(db_session)
    api_key_obj, raw_key = await service.create("Other User Key")
    response = await client.post("/auth/token", json={"api_key": raw_key})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def valid_workflow_payload(name: str = "Test Workflow"):
    return {
        "name": name,
        "description": "Test Desc",
        "definition": {
            "name": name,
            "nodes": [
                {"id": "n1", "type": "delay", "config": {"duration_seconds": 1}},
                {"id": "n2", "type": "delay", "config": {"duration_seconds": 2}},
            ],
            "edges": [{"from": "n1", "to": "n2"}],
        },
    }


def invalid_workflow_payload():
    return {
        "name": "Invalid Cyclic",
        "description": "Fail",
        "definition": {
            "name": "Cyclic",
            "nodes": [
                {"id": "n1", "type": "delay", "config": {"duration_seconds": 1}},
                {"id": "n2", "type": "delay", "config": {"duration_seconds": 1}},
            ],
            "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n1"}],
        },
    }


@pytest.mark.anyio
async def test_create_valid_workflow(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/workflows", json=valid_workflow_payload(), headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["version_number"] == 1
    assert data["workflow_id"] is not None
    assert data["checksum"] is not None


@pytest.mark.anyio
async def test_reject_invalid_workflow(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/workflows", json=invalid_workflow_payload(), headers=auth_headers
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "cycle_detected"


@pytest.mark.anyio
async def test_workflow_versions_and_immutability(client: AsyncClient, auth_headers: dict):
    # Create workflow
    payload = valid_workflow_payload("V1")
    resp = await client.post("/api/v1/workflows", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    v1_data = resp.json()
    workflow_id = v1_data["workflow_id"]

    # Append version 2
    v2_def = payload["definition"]
    v2_def["nodes"].append({"id": "n3", "type": "delay", "config": {"duration_seconds": 3}})
    v2_def["edges"].append({"from": "n2", "to": "n3"})

    resp2 = await client.post(
        f"/api/v1/workflows/{workflow_id}/versions",
        json={"definition": v2_def},
        headers=auth_headers,
    )
    assert resp2.status_code == 201
    v2_data = resp2.json()

    assert v2_data["version_number"] == 2
    assert v2_data["checksum"] != v1_data["checksum"]

    # Verify detail
    resp3 = await client.get(f"/api/v1/workflows/{workflow_id}", headers=auth_headers)
    assert resp3.status_code == 200
    detail = resp3.json()
    assert len(detail["versions"]) == 2
    assert detail["versions"][0]["version_number"] == 2
    assert detail["versions"][1]["version_number"] == 1
    assert detail["versions"][1]["checksum"] == v1_data["checksum"]  # unchanged


@pytest.mark.anyio
async def test_list_workflows(client: AsyncClient, auth_headers: dict):
    # Ensure there's at least one
    await client.post(
        "/api/v1/workflows", json=valid_workflow_payload("List1"), headers=auth_headers
    )

    resp = await client.get("/api/v1/workflows", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1

    wf = data[0]
    assert "latest_version_number" in wf
    assert wf["latest_version_number"] >= 1


@pytest.mark.anyio
async def test_ownership_boundary(
    client: AsyncClient, auth_headers: dict, other_auth_headers: dict
):
    # Create workflow as user A
    resp = await client.post(
        "/api/v1/workflows", json=valid_workflow_payload("User A"), headers=auth_headers
    )
    workflow_id = resp.json()["workflow_id"]

    # Try to access as user B
    resp_get = await client.get(f"/api/v1/workflows/{workflow_id}", headers=other_auth_headers)
    assert resp_get.status_code == 404

    # Try to append version as user B
    resp_post = await client.post(
        f"/api/v1/workflows/{workflow_id}/versions",
        json={"definition": valid_workflow_payload()["definition"]},
        headers=other_auth_headers,
    )
    assert resp_post.status_code == 404

    # List workflows as user B should not contain user A's workflow
    resp_list = await client.get("/api/v1/workflows", headers=other_auth_headers)
    assert resp_list.status_code == 200
    assert not any(w["id"] == workflow_id for w in resp_list.json())


@pytest.mark.anyio
async def test_deterministic_checksum(client: AsyncClient, auth_headers: dict):
    # Creating same definition multiple times should yield same checksum
    payload = valid_workflow_payload()

    # Create workflow 1
    resp1 = await client.post("/api/v1/workflows", json=payload, headers=auth_headers)
    chk1 = resp1.json()["checksum"]

    # Create workflow 2
    resp2 = await client.post("/api/v1/workflows", json=payload, headers=auth_headers)
    chk2 = resp2.json()["checksum"]

    assert chk1 == chk2
