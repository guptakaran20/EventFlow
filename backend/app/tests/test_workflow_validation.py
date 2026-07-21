import uuid

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.core.security import AuthenticatedPrincipal, require_api_key
from app.main import app


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[require_api_key] = lambda: AuthenticatedPrincipal(
        api_key_id=uuid.uuid4()
    )
    yield
    app.dependency_overrides.pop(require_api_key, None)


@pytest.fixture
def auth_headers():
    settings = get_settings()
    return {settings.api_key_header_name: "test-key"}


@pytest.mark.anyio
async def test_validate_linear_workflow(client: AsyncClient, auth_headers: dict):
    payload = {
        "name": "Linear Workflow",
        "description": "A simple linear workflow",
        "nodes": [
            {"id": "node-1", "type": "http", "config": {"url": "https://example.com"}},
            {"id": "node-2", "type": "delay", "config": {"duration_seconds": 5}},
        ],
        "edges": [{"from": "node-1", "to": "node-2"}],
    }

    resp = await client.post("/api/v1/workflows/validate", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["root_nodes"] == ["node-1"]
    assert data["topological_order"] == ["node-1", "node-2"]


@pytest.mark.anyio
async def test_validate_branching_workflow(client: AsyncClient, auth_headers: dict):
    payload = {
        "name": "Branching Workflow",
        "nodes": [
            {"id": "root", "type": "http", "config": {"url": "https://example.com"}},
            {"id": "branch-a", "type": "delay", "config": {"duration_seconds": 1}},
            {"id": "branch-b", "type": "delay", "config": {"duration_seconds": 2}},
        ],
        "edges": [{"from": "root", "to": "branch-a"}, {"from": "root", "to": "branch-b"}],
    }

    resp = await client.post("/api/v1/workflows/validate", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["root_nodes"] == ["root"]
    assert "root" in data["topological_order"]


@pytest.mark.anyio
async def test_duplicate_node_ids(client: AsyncClient, auth_headers: dict):
    payload = {
        "name": "Duplicate Node ID",
        "nodes": [
            {"id": "node-1", "type": "http", "config": {"url": "https://example.com"}},
            {"id": "node-1", "type": "delay", "config": {"duration_seconds": 5}},
        ],
        "edges": [],
    }

    resp = await client.post("/api/v1/workflows/validate", json=payload, headers=auth_headers)
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["code"] == "duplicate_node_id"
    assert "Duplicate node ID detected" in error["message"]


@pytest.mark.anyio
async def test_missing_edge_reference(client: AsyncClient, auth_headers: dict):
    payload = {
        "name": "Missing Edge Reference",
        "nodes": [
            {"id": "node-1", "type": "http", "config": {"url": "https://example.com"}},
        ],
        "edges": [{"from": "node-1", "to": "non-existent"}],
    }

    resp = await client.post("/api/v1/workflows/validate", json=payload, headers=auth_headers)
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["code"] == "missing_edge_reference"
    assert "missing target node" in error["message"]


@pytest.mark.anyio
async def test_cyclic_workflow(client: AsyncClient, auth_headers: dict):
    payload = {
        "name": "Cyclic Workflow",
        "nodes": [
            {"id": "node-1", "type": "http", "config": {"url": "https://example.com"}},
            {"id": "node-2", "type": "delay", "config": {"duration_seconds": 1}},
        ],
        "edges": [{"from": "node-1", "to": "node-2"}, {"from": "node-2", "to": "node-1"}],
    }

    resp = await client.post("/api/v1/workflows/validate", json=payload, headers=auth_headers)
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["code"] == "cycle_detected"
    assert "contains a cycle" in error["message"]


@pytest.mark.anyio
async def test_unknown_executor_type(client: AsyncClient, auth_headers: dict):
    payload = {
        "name": "Unknown Executor Type",
        "nodes": [
            {"id": "node-1", "type": "quantum_computer", "config": {}},
        ],
        "edges": [],
    }

    resp = await client.post("/api/v1/workflows/validate", json=payload, headers=auth_headers)
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["code"] == "unknown_executor_type"
    assert "Unknown executor type" in error["message"]


@pytest.mark.anyio
async def test_invalid_executor_config(client: AsyncClient, auth_headers: dict):
    payload = {
        "name": "Invalid Executor Config",
        "nodes": [
            {"id": "node-1", "type": "http", "config": {"wrong_key": "val"}},
        ],
        "edges": [],
    }

    resp = await client.post("/api/v1/workflows/validate", json=payload, headers=auth_headers)
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["code"] == "invalid_executor_config"
    assert "Invalid config for node" in error["message"]
