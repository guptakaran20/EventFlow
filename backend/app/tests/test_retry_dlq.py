import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_session_factory
from app.models import (
    APIKey,
    DeadLetterJob,
    Execution,
    ExecutionStatus,
    NodeExecution,
    NodeExecutionStatus,
    Workflow,
    WorkflowVersion,
)
from app.queue.publisher import InMemoryQueuePublisher, serialize_job_payload
from app.schemas.workflow import Node, RetryPolicy, WorkflowDefinition
from app.services.executor_registry import ExecutionContext, ExecutorRegistry, ExecutorResult
from app.services.retry_policy import resolve_retry_policy
from app.worker.runtime import process_job


class FailingExecutor:
    type = "always_fail"

    def validate_config(self, config: dict) -> None:
        pass

    async def execute(self, context: ExecutionContext) -> ExecutorResult:
        return ExecutorResult(success=False, error="boom")


def make_registry() -> ExecutorRegistry:
    registry = ExecutorRegistry()
    registry.register(FailingExecutor())
    return registry


# --- Retry policy resolution (pure, no DB) ---------------------------------


def test_node_retry_policy_overrides_workflow_default():
    node = Node(id="n1", type="http", config={}, retry_policy=RetryPolicy(max_attempts=5))
    definition = WorkflowDefinition(
        name="wf", nodes=[node], default_retry_policy=RetryPolicy(max_attempts=2)
    )
    assert resolve_retry_policy(node, definition).max_attempts == 5


def test_workflow_default_retry_policy_applies_when_node_absent():
    node = Node(id="n1", type="http", config={})
    definition = WorkflowDefinition(
        name="wf", nodes=[node], default_retry_policy=RetryPolicy(max_attempts=7)
    )
    assert resolve_retry_policy(node, definition).max_attempts == 7


def test_safe_default_retry_policy_when_nothing_specified():
    node = Node(id="n1", type="http", config={})
    definition = WorkflowDefinition(name="wf", nodes=[node])
    assert resolve_retry_policy(node, definition).max_attempts == 3


# --- Worker retry/DLQ behavior (DB-backed) ----------------------------------


@pytest.fixture
async def db(engine) -> AsyncSession:
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


async def _make_execution(
    db: AsyncSession,
    definition: dict,
    node_statuses: dict[str, NodeExecutionStatus],
    max_attempts_by_id: dict[str, int] | None = None,
) -> tuple[Execution, dict[str, NodeExecution]]:
    api_key = APIKey(name="retry-test", key_hash=f"hash-{uuid.uuid4()}", is_active=True)
    db.add(api_key)
    await db.flush()

    workflow = Workflow(owner_api_key_id=api_key.id, name="wf", description="")
    db.add(workflow)
    await db.flush()

    version = WorkflowVersion(
        workflow_id=workflow.id, version_number=1, definition=definition, checksum="deadbeef"
    )
    db.add(version)
    await db.flush()

    execution = Execution(
        workflow_id=workflow.id,
        workflow_version_id=version.id,
        status=ExecutionStatus.RUNNING,
        input_payload={},
    )
    db.add(execution)
    await db.flush()

    max_attempts_by_id = max_attempts_by_id or {}
    nodes_by_id = {}
    for node in definition["nodes"]:
        status = node_statuses.get(node["id"], NodeExecutionStatus.PENDING)
        node_exec = NodeExecution(
            execution_id=execution.id,
            node_id=node["id"],
            node_type=node["type"],
            status=status,
            attempt=1 if status == NodeExecutionStatus.QUEUED else 0,
            max_attempts=max_attempts_by_id.get(node["id"], 1),
        )
        db.add(node_exec)
        nodes_by_id[node["id"]] = node_exec
    await db.flush()

    return execution, nodes_by_id


@pytest.mark.asyncio
async def test_retry_until_exhaustion_then_dead_letters(db: AsyncSession):
    definition = {
        "name": "retry-flow",
        "nodes": [
            {"id": "node1", "type": "always_fail", "config": {}},
            {"id": "node2", "type": "always_fail", "config": {}},
        ],
        "edges": [{"from": "node1", "to": "node2"}],
    }
    execution, nodes = await _make_execution(
        db, definition, {"node1": NodeExecutionStatus.QUEUED}, max_attempts_by_id={"node1": 3}
    )
    node1 = nodes["node1"]
    assert node1.attempt == 1

    publisher = InMemoryQueuePublisher()
    registry = make_registry()
    fields = serialize_job_payload(
        execution.id, node1.id, execution.workflow_version_id, "node1", node1.attempt
    )

    # Attempt 1 fails -> retried -> attempt becomes 2, requeued for the same node
    await process_job(db, registry, publisher, fields)
    await db.refresh(node1)
    assert node1.status == NodeExecutionStatus.QUEUED
    assert node1.attempt == 2
    assert len(publisher.published_jobs) == 1
    assert publisher.published_jobs[-1]["node_id"] == "node1"
    assert publisher.published_jobs[-1]["execution_id"] == str(execution.id)
    assert publisher.published_jobs[-1]["attempt"] == 2

    # Attempt 2 fails -> retried -> attempt becomes 3
    await process_job(db, registry, publisher, fields)
    await db.refresh(node1)
    assert node1.status == NodeExecutionStatus.QUEUED
    assert node1.attempt == 3
    assert len(publisher.published_jobs) == 2

    # Attempt 3 fails -> attempts exhausted (3 >= max_attempts 3) -> DEAD_LETTERED
    await process_job(db, registry, publisher, fields)
    await db.refresh(node1)
    assert node1.status == NodeExecutionStatus.DEAD_LETTERED
    assert node1.attempt == 3
    assert len(publisher.published_jobs) == 2  # no further requeue on dead-letter

    await db.refresh(execution)
    assert execution.status == ExecutionStatus.FAILED

    dlq_jobs = (
        (await db.execute(select(DeadLetterJob).where(DeadLetterJob.node_execution_id == node1.id)))
        .scalars()
        .all()
    )
    assert len(dlq_jobs) == 1
    assert dlq_jobs[0].attempts == 3
    assert dlq_jobs[0].execution_id == execution.id

    # Downstream node2 must never be queued after its parent failed/dead-lettered
    await db.refresh(nodes["node2"])
    assert nodes["node2"].status == NodeExecutionStatus.PENDING


@pytest.mark.asyncio
async def test_ack_happens_after_retry_state_committed(engine):
    """Redis ACK ordering: retry requeue must be durably committed before ack."""
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as setup_session:
        definition = {
            "name": "retry-ack-order",
            "nodes": [{"id": "node1", "type": "always_fail", "config": {}}],
            "edges": [],
        }
        execution, nodes = await _make_execution(
            setup_session,
            definition,
            {"node1": NodeExecutionStatus.QUEUED},
            max_attempts_by_id={"node1": 2},
        )
        node1_id = nodes["node1"].id
        await setup_session.commit()

    async with session_factory() as session:
        fields = serialize_job_payload(
            execution.id, node1_id, execution.workflow_version_id, "node1", 1
        )
        await process_job(session, make_registry(), InMemoryQueuePublisher(), fields)

    async with session_factory() as check_session:
        node1 = await check_session.get(NodeExecution, node1_id)
        assert node1.status == NodeExecutionStatus.QUEUED
        assert node1.attempt == 2


# --- DLQ API ownership + resolve --------------------------------------------


@pytest.fixture
async def other_auth_headers(client, db_session):
    from app.services.api_key_service import APIKeyService

    service = APIKeyService(db_session)
    api_key_obj, raw_key = await service.create("Other User Key")
    response = await client.post("/api/v1/auth/token", json={"api_key": raw_key})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def owned_execution_ids(client: AsyncClient, auth_headers: dict):
    payload = {
        "name": "DLQ Test Workflow",
        "description": "",
        "definition": {
            "name": "DLQ Test Workflow",
            "nodes": [{"id": "node1", "type": "delay", "config": {"duration_seconds": 0.01}}],
            "edges": [],
        },
    }
    resp = await client.post("/api/v1/workflows", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    workflow_version_id = resp.json()["id"]

    from app.main import app as fastapi_app
    from app.transport.local_execution_client import get_queue_publisher

    fastapi_app.dependency_overrides[get_queue_publisher] = lambda: InMemoryQueuePublisher()
    try:
        exec_resp = await client.post(
            "/api/v1/executions",
            json={"workflow_version_id": workflow_version_id, "input_payload": {}},
            headers=auth_headers,
        )
        assert exec_resp.status_code == 201
        execution_id = exec_resp.json()["id"]
        node_execution_id = exec_resp.json()["node_executions"][0]["id"]
    finally:
        fastapi_app.dependency_overrides.pop(get_queue_publisher, None)

    return execution_id, node_execution_id


@pytest.fixture
async def dlq_job_id(owned_execution_ids: tuple[str, str]) -> uuid.UUID:
    execution_id, node_execution_id = owned_execution_ids
    session_factory = get_session_factory()
    async with session_factory() as session:
        job = DeadLetterJob(
            execution_id=uuid.UUID(execution_id),
            node_execution_id=uuid.UUID(node_execution_id),
            reason="max attempts exceeded",
            attempts=3,
            payload={"node_id": "node1"},
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job.id


@pytest.mark.asyncio
async def test_dlq_list_and_detail_enforce_ownership(
    client: AsyncClient,
    dlq_job_id: uuid.UUID,
    auth_headers: dict,
    other_auth_headers: dict,
):
    list_resp = await client.get("/api/v1/dlq", headers=auth_headers)
    assert list_resp.status_code == 200
    ids = [item["id"] for item in list_resp.json()]
    assert str(dlq_job_id) in ids

    detail_resp = await client.get(f"/api/v1/dlq/{dlq_job_id}", headers=auth_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["reason"] == "max attempts exceeded"
    assert detail_resp.json()["attempts"] == 3

    other_list_resp = await client.get("/api/v1/dlq", headers=other_auth_headers)
    assert other_list_resp.status_code == 200
    assert str(dlq_job_id) not in [item["id"] for item in other_list_resp.json()]

    other_detail_resp = await client.get(f"/api/v1/dlq/{dlq_job_id}", headers=other_auth_headers)
    assert other_detail_resp.status_code == 404


@pytest.mark.asyncio
async def test_dlq_resolve_sets_resolved_at_and_note(
    client: AsyncClient, dlq_job_id: uuid.UUID, auth_headers: dict
):
    resp = await client.post(
        f"/api/v1/dlq/{dlq_job_id}/resolve",
        json={"resolution_note": "manually replayed"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["resolution_note"] == "manually replayed"
    assert data["resolved_at"] is not None
