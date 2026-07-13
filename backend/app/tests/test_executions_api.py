import uuid

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.main import app as fastapi_app
from app.queue.publisher import InMemoryQueuePublisher
from app.transport.local_execution_client import get_queue_publisher


@pytest.fixture(autouse=True)
def setup_bootstrap_keys():
    settings = get_settings()
    original_keys = settings.bootstrap_api_keys
    settings.bootstrap_api_keys = "test-key,other-bootstrap-key"
    yield
    settings.bootstrap_api_keys = original_keys


@pytest.fixture
def auth_headers():
    settings = get_settings()
    return {settings.api_key_header_name: "test-key"}


@pytest.fixture
def other_auth_headers():
    settings = get_settings()
    return {settings.api_key_header_name: "other-bootstrap-key"}


@pytest.fixture
async def test_workflow_version_id(client: AsyncClient, auth_headers: dict):
    payload = {
        "name": "Test Workflow",
        "description": "Test Desc",
        "definition": {
            "name": "Test Workflow",
            "nodes": [
                {"id": "node1", "type": "delay", "config": {"duration_seconds": 1}},
                {"id": "node2", "type": "delay", "config": {"duration_seconds": 2}},
                {"id": "node3", "type": "delay", "config": {"duration_seconds": 3}},
            ],
            "edges": [{"from": "node1", "to": "node2"}, {"from": "node1", "to": "node3"}],
        },
    }
    resp = await client.post("/api/v1/workflows", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture
def execution_payload(test_workflow_version_id):
    return {"workflow_version_id": test_workflow_version_id, "input_payload": {"hello": "world"}}


@pytest.fixture
def mock_queue_publisher():
    publisher = InMemoryQueuePublisher()
    fastapi_app.dependency_overrides[get_queue_publisher] = lambda: publisher
    yield publisher
    fastapi_app.dependency_overrides.pop(get_queue_publisher, None)


@pytest.mark.asyncio
async def test_create_execution(
    client: AsyncClient,
    execution_payload: dict,
    auth_headers: dict,
    mock_queue_publisher: InMemoryQueuePublisher,
):
    resp = await client.post("/api/v1/executions", json=execution_payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["workflow_version_id"] == execution_payload["workflow_version_id"]
    assert data["status"] == "RUNNING"
    assert data["input_payload"] == {"hello": "world"}
    assert "id" in data

    # Assert node_executions in POST response
    assert "node_executions" in data
    assert len(data["node_executions"]) == 3

    # Verify node executions
    execution_id = data["id"]
    nodes_resp = await client.get(f"/api/v1/executions/{execution_id}/nodes", headers=auth_headers)
    assert nodes_resp.status_code == 200
    nodes = nodes_resp.json()

    assert len(nodes) == 3

    queued_nodes = [n for n in nodes if n["status"] == "QUEUED"]
    pending_nodes = [n for n in nodes if n["status"] == "PENDING"]

    assert len(queued_nodes) == 1
    assert queued_nodes[0]["node_id"] == "node1"
    assert queued_nodes[0]["attempt"] == 1

    assert len(pending_nodes) == 2
    for node in pending_nodes:
        assert node["attempt"] == 0

    assert len(mock_queue_publisher.published_jobs) == 1
    published = mock_queue_publisher.published_jobs[0]
    assert published["execution_id"] == execution_id
    assert published["node_id"] == "node1"
    assert published["attempt"] == 1


@pytest.mark.asyncio
async def test_get_execution(client: AsyncClient, execution_payload: dict, auth_headers: dict):
    create_resp = await client.post(
        "/api/v1/executions", json=execution_payload, headers=auth_headers
    )
    assert create_resp.status_code == 201
    execution_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/executions/{execution_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == execution_id
    assert data["status"] == "RUNNING"


@pytest.mark.asyncio
async def test_get_execution_unauthorized(
    client: AsyncClient, test_workflow_version_id: str, other_auth_headers: dict
):
    payload = {"workflow_version_id": test_workflow_version_id, "input_payload": {}}
    resp = await client.post("/api/v1/executions", json=payload, headers=other_auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_execution_not_found(client: AsyncClient, auth_headers: dict):
    payload = {"workflow_version_id": str(uuid.uuid4()), "input_payload": {}}
    resp = await client.post("/api/v1/executions", json=payload, headers=auth_headers)
    assert resp.status_code == 404
