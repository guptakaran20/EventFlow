import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    APIKey,
    DeadLetterJob,
    Execution,
    ExecutionLog,
    ExecutionStatus,
    LogLevel,
    NodeExecution,
    NodeExecutionStatus,
    Worker,
    WorkerStatus,
    Workflow,
    WorkflowVersion,
)

# Engine is now in conftest.py


@pytest.fixture
async def db(engine) -> AsyncSession:
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


async def _make_api_key(db: AsyncSession, name: str = "test-key") -> APIKey:
    api_key = APIKey(name=name, key_hash=f"hash-{uuid.uuid4()}", is_active=True)
    db.add(api_key)
    await db.flush()
    return api_key


async def _make_workflow(db: AsyncSession, api_key: APIKey) -> Workflow:
    workflow = Workflow(owner_api_key_id=api_key.id, name="wf", description="desc")
    db.add(workflow)
    await db.flush()
    return workflow


async def _make_workflow_version(
    db: AsyncSession, workflow: Workflow, version_number: int = 1
) -> WorkflowVersion:
    version = WorkflowVersion(
        workflow_id=workflow.id,
        version_number=version_number,
        definition={"nodes": [], "edges": []},
        checksum="deadbeef",
    )
    db.add(version)
    await db.flush()
    return version


async def test_create_api_key(db: AsyncSession):
    api_key = await _make_api_key(db)
    assert api_key.id is not None
    assert api_key.is_active is True
    assert api_key.created_at is not None


async def test_create_workflow_and_version_relationship(db: AsyncSession):
    api_key = await _make_api_key(db)
    workflow = await _make_workflow(db, api_key)
    version = await _make_workflow_version(db, workflow)

    await db.refresh(workflow, attribute_names=["versions"])
    assert workflow.owner_api_key_id == api_key.id
    assert len(workflow.versions) == 1
    assert workflow.versions[0].id == version.id


async def test_workflow_version_unique_constraint(db: AsyncSession):
    api_key = await _make_api_key(db)
    workflow = await _make_workflow(db, api_key)
    await _make_workflow_version(db, workflow, version_number=1)

    duplicate = WorkflowVersion(
        workflow_id=workflow.id,
        version_number=1,
        definition={},
        checksum="other",
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_execution_and_node_execution_relationship(db: AsyncSession):
    api_key = await _make_api_key(db)
    workflow = await _make_workflow(db, api_key)
    version = await _make_workflow_version(db, workflow)

    execution = Execution(
        workflow_id=workflow.id,
        workflow_version_id=version.id,
        status=ExecutionStatus.CREATED,
    )
    db.add(execution)
    await db.flush()

    node_execution = NodeExecution(
        execution_id=execution.id,
        node_id="node-1",
        node_type="http",
        status=NodeExecutionStatus.PENDING,
    )
    db.add(node_execution)
    await db.flush()

    await db.refresh(execution, attribute_names=["node_executions"])
    assert execution.status == ExecutionStatus.CREATED
    assert len(execution.node_executions) == 1
    assert execution.node_executions[0].node_id == "node-1"


async def test_node_execution_unique_constraint(db: AsyncSession):
    api_key = await _make_api_key(db)
    workflow = await _make_workflow(db, api_key)
    version = await _make_workflow_version(db, workflow)
    execution = Execution(workflow_id=workflow.id, workflow_version_id=version.id)
    db.add(execution)
    await db.flush()

    db.add(NodeExecution(execution_id=execution.id, node_id="node-1", node_type="http"))
    await db.flush()

    db.add(NodeExecution(execution_id=execution.id, node_id="node-1", node_type="http"))
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_execution_log_relationships(db: AsyncSession):
    api_key = await _make_api_key(db)
    workflow = await _make_workflow(db, api_key)
    version = await _make_workflow_version(db, workflow)
    execution = Execution(workflow_id=workflow.id, workflow_version_id=version.id)
    db.add(execution)
    await db.flush()

    node_execution = NodeExecution(execution_id=execution.id, node_id="node-1", node_type="http")
    db.add(node_execution)
    await db.flush()

    log = ExecutionLog(
        execution_id=execution.id,
        node_execution_id=node_execution.id,
        level=LogLevel.INFO,
        event_type="node_queued",
        message="queued",
        log_metadata={"key": "value"},
    )
    db.add(log)
    await db.flush()

    assert log.id is not None
    assert log.log_metadata == {"key": "value"}


async def test_worker_and_dead_letter_job(db: AsyncSession):
    api_key = await _make_api_key(db)
    workflow = await _make_workflow(db, api_key)
    version = await _make_workflow_version(db, workflow)
    execution = Execution(workflow_id=workflow.id, workflow_version_id=version.id)
    db.add(execution)
    await db.flush()

    worker = Worker(worker_name=f"worker-{uuid.uuid4()}", status=WorkerStatus.IDLE)
    db.add(worker)
    await db.flush()

    node_execution = NodeExecution(
        execution_id=execution.id,
        node_id="node-1",
        node_type="http",
        worker_id=worker.id,
    )
    db.add(node_execution)
    await db.flush()

    dlq_job = DeadLetterJob(
        execution_id=execution.id,
        node_execution_id=node_execution.id,
        reason="max attempts exceeded",
        attempts=3,
        payload={"error": "timeout"},
    )
    db.add(dlq_job)
    await db.flush()

    assert dlq_job.id is not None
    assert node_execution.worker_id == worker.id


async def test_expected_indexes_exist(db: AsyncSession):
    result = await db.execute(text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"))
    index_names = {row[0] for row in result.fetchall()}

    expected = {
        "ix_executions_status",
        "ix_executions_workflow_version_id",
        "ix_node_executions_execution_id_status",
        "ix_node_executions_idempotency_key",
        "ix_execution_logs_execution_id_created_at",
        "ix_dead_letter_jobs_resolved_at",
        "ix_workers_last_heartbeat_at",
    }
    assert expected.issubset(index_names)
