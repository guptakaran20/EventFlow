import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.main import app as fastapi_app
from app.models import DeadLetterJob, ExecutionLog, LogLevel
from app.queue.publisher import InMemoryQueuePublisher
from app.services.worker_service import WorkerService
from app.transport.local_execution_client import get_queue_publisher


@pytest.fixture
async def other_auth_headers(client, db_session):
    from app.services.api_key_service import APIKeyService

    service = APIKeyService(db_session)
    api_key_obj, raw_key = await service.create("Other User Key")
    response = await client.post("/api/v1/auth/token", json={"api_key": raw_key})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def db(engine) -> AsyncSession:
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def owned_execution(client: AsyncClient, auth_headers: dict):
    payload = {
        "name": "Observability Test Workflow",
        "description": "",
        "definition": {
            "name": "Observability Test Workflow",
            "nodes": [{"id": "node1", "type": "delay", "config": {"duration_seconds": 0.01}}],
            "edges": [],
        },
    }
    resp = await client.post("/api/v1/workflows", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    workflow_version_id = resp.json()["id"]

    fastapi_app.dependency_overrides[get_queue_publisher] = lambda: InMemoryQueuePublisher()
    try:
        exec_resp = await client.post(
            "/api/v1/executions",
            json={"workflow_version_id": workflow_version_id, "input_payload": {}},
            headers=auth_headers,
        )
        assert exec_resp.status_code == 201
        body = exec_resp.json()
        return body["id"], body["node_executions"][0]["id"]
    finally:
        fastapi_app.dependency_overrides.pop(get_queue_publisher, None)


@pytest.fixture
def owned_execution_id(owned_execution):
    return owned_execution[0]


# --- Execution logs API ------------------------------------------------------


@pytest.mark.asyncio
async def test_execution_logs_ownership_enforced(
    client: AsyncClient,
    owned_execution_id: str,
    auth_headers: dict,
    other_auth_headers: dict,
):
    resp = await client.get(
        f"/api/v1/executions/{owned_execution_id}/logs", headers=other_auth_headers
    )
    assert resp.status_code == 404

    resp = await client.get(f"/api/v1/executions/{owned_execution_id}/logs", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_execution_logs_ordered_by_created_at_asc(
    client: AsyncClient, owned_execution_id: str, auth_headers: dict, db: AsyncSession
):
    execution_id = uuid.UUID(owned_execution_id)
    for i in range(3):
        db.add(
            ExecutionLog(
                execution_id=execution_id,
                level=LogLevel.INFO,
                event_type="test_event",
                message=f"event {i}",
            )
        )
        await db.commit()

    resp = await client.get(f"/api/v1/executions/{owned_execution_id}/logs", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 3
    timestamps = [item["timestamp"] for item in body]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_execution_logs_pagination(
    client: AsyncClient, owned_execution_id: str, auth_headers: dict, db: AsyncSession
):
    execution_id = uuid.UUID(owned_execution_id)
    for i in range(5):
        db.add(
            ExecutionLog(
                execution_id=execution_id,
                level=LogLevel.INFO,
                event_type="page_test",
                message=f"page event {i}",
            )
        )
    await db.commit()

    full_resp = await client.get(
        f"/api/v1/executions/{owned_execution_id}/logs",
        params={"limit": 100, "offset": 0},
        headers=auth_headers,
    )
    full_body = full_resp.json()

    page1 = await client.get(
        f"/api/v1/executions/{owned_execution_id}/logs",
        params={"limit": 2, "offset": 0},
        headers=auth_headers,
    )
    page2 = await client.get(
        f"/api/v1/executions/{owned_execution_id}/logs",
        params={"limit": 2, "offset": 2},
        headers=auth_headers,
    )
    assert len(page1.json()) == 2
    assert len(page2.json()) == 2
    assert page1.json() == full_body[0:2]
    assert page2.json() == full_body[2:4]


# --- Execution timeline -------------------------------------------------------


@pytest.mark.asyncio
async def test_execution_timeline_chronological(
    client: AsyncClient, owned_execution_id: str, auth_headers: dict, db: AsyncSession
):
    execution_id = uuid.UUID(owned_execution_id)
    for i in range(4):
        db.add(
            ExecutionLog(
                execution_id=execution_id,
                level=LogLevel.INFO,
                event_type="timeline_test",
                message=f"timeline event {i}",
            )
        )
    await db.commit()

    resp = await client.get(
        f"/api/v1/executions/{owned_execution_id}/timeline", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 4
    timestamps = [item["timestamp"] for item in body]
    assert timestamps == sorted(timestamps)
    for item in body:
        assert set(["timestamp", "level", "message", "metadata"]).issubset(item.keys())


# --- Worker API ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_worker_list_shows_heartbeat_age(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
):
    service = WorkerService(db)
    worker = await service.register_worker("observability-worker", "obs-host")

    resp = await client.get("/api/v1/workers", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    match = next(w for w in body if w["worker_id"] == str(worker.id))
    assert match["heartbeat_age_seconds"] is not None
    assert match["heartbeat_age_seconds"] >= 0
    assert "hostname" in match
    assert "current_job_id" in match
    assert "started_at" in match
    assert "last_heartbeat_at" in match


# --- Metrics summary API -------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_summary_endpoint(
    client: AsyncClient, owned_execution: tuple[str, str], auth_headers: dict, db: AsyncSession
):
    execution_id, node_execution_id = owned_execution
    db.add(
        DeadLetterJob(
            execution_id=uuid.UUID(execution_id),
            node_execution_id=uuid.UUID(node_execution_id),
            reason="test failure",
            attempts=3,
        )
    )
    await db.commit()

    resp = await client.get("/api/v1/metrics/summary", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "active_executions",
        "queued_nodes",
        "running_nodes",
        "workers",
        "active_workers",
        "queue_depth",
        "dead_letter_jobs",
    ):
        assert key in body
        assert isinstance(body[key], int)
    assert body["active_executions"] >= 1
    assert body["dead_letter_jobs"] >= 1


@pytest.mark.asyncio
async def test_metrics_summary_scoped_to_owner(
    client: AsyncClient, owned_execution_id: str, auth_headers: dict, other_auth_headers: dict
):
    mine = (await client.get("/api/v1/metrics/summary", headers=auth_headers)).json()
    theirs = (await client.get("/api/v1/metrics/summary", headers=other_auth_headers)).json()
    assert mine["active_executions"] >= 1
    assert theirs["active_executions"] == 0


# --- DLQ ownership continues to hold -------------------------------------------


@pytest.mark.asyncio
async def test_dlq_ownership_still_enforced_via_observability_flow(
    client: AsyncClient,
    owned_execution: tuple[str, str],
    auth_headers: dict,
    other_auth_headers: dict,
    db: AsyncSession,
):
    execution_id, node_execution_id = owned_execution
    job = DeadLetterJob(
        execution_id=uuid.UUID(execution_id),
        node_execution_id=uuid.UUID(node_execution_id),
        reason="dlq ownership check",
        attempts=1,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    mine = await client.get("/api/v1/dlq", headers=auth_headers)
    assert str(job.id) in [item["id"] for item in mine.json()]

    theirs = await client.get("/api/v1/dlq", headers=other_auth_headers)
    assert str(job.id) not in [item["id"] for item in theirs.json()]
