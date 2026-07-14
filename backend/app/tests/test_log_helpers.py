import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import APIKey, Execution, NodeExecution, Workflow, WorkflowVersion
from app.models.enums import LogLevel
from app.models.log import ExecutionLog
from app.observability import log_helpers


@pytest.fixture
async def db(engine) -> AsyncSession:
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def execution_and_node(db: AsyncSession) -> tuple[Execution, NodeExecution]:
    api_key = APIKey(name="log-helpers-test", key_hash=f"hash-{uuid.uuid4()}", is_active=True)
    db.add(api_key)
    await db.flush()

    workflow = Workflow(owner_api_key_id=api_key.id, name="wf", description="")
    db.add(workflow)
    await db.flush()

    version = WorkflowVersion(
        workflow_id=workflow.id,
        version_number=1,
        definition={"name": "wf", "nodes": [], "edges": []},
        checksum="deadbeef",
    )
    db.add(version)
    await db.flush()

    execution = Execution(workflow_id=workflow.id, workflow_version_id=version.id)
    db.add(execution)
    await db.flush()

    node = NodeExecution(execution_id=execution.id, node_id="node1", node_type="http")
    db.add(node)
    await db.flush()

    return execution, node


@pytest.mark.asyncio
async def test_execution_started_creates_log(
    db: AsyncSession, execution_and_node: tuple[Execution, NodeExecution]
):
    execution, _ = execution_and_node
    log_helpers.execution_started(db, execution.id)
    await db.flush()

    stored = (
        await db.execute(select(ExecutionLog).where(ExecutionLog.execution_id == execution.id))
    ).scalar_one()
    assert stored.event_type == log_helpers.EVENT_EXECUTION_STARTED
    assert stored.level == LogLevel.INFO
    assert stored.node_execution_id is None


@pytest.mark.asyncio
async def test_node_failed_and_dead_lettered_include_metadata(
    db: AsyncSession, execution_and_node: tuple[Execution, NodeExecution]
):
    execution, node = execution_and_node

    log_helpers.node_failed(db, execution.id, node.id, "node1", "boom")
    log_helpers.dead_lettered(db, execution.id, node.id, "node1", "max attempts exceeded")
    await db.flush()

    logs = (
        (
            await db.execute(
                select(ExecutionLog)
                .where(ExecutionLog.node_execution_id == node.id)
                .order_by(ExecutionLog.event_type)
            )
        )
        .scalars()
        .all()
    )
    by_type = {log.event_type: log for log in logs}
    assert by_type[log_helpers.EVENT_NODE_FAILED].level == LogLevel.ERROR
    assert by_type[log_helpers.EVENT_NODE_FAILED].log_metadata["error"] == "boom"
    assert (
        by_type[log_helpers.EVENT_DEAD_LETTERED].log_metadata["reason"] == "max attempts exceeded"
    )
