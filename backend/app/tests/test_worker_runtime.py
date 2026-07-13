import asyncio
import uuid

import pytest
from redis.exceptions import ResponseError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from app.services.executor_registry import (
    ConditionExecutor,
    DelayExecutor,
    ExecutionContext,
    ExecutorRegistry,
    ExecutorResult,
)
from app.worker.runtime import process_job, run_worker


class FailingExecutor:
    type = "always_fail"

    def validate_config(self, config: dict) -> None:
        pass

    async def execute(self, context: ExecutionContext) -> ExecutorResult:
        return ExecutorResult(success=False, error="boom")


class NeverCallExecutor:
    """Spy executor: fails the test if the worker ever invokes it."""

    type = "delay"

    def validate_config(self, config: dict) -> None:
        pass

    async def execute(self, context: ExecutionContext) -> ExecutorResult:
        raise AssertionError("executor should not run for a terminal duplicate job")


class FakeRedis:
    """Minimal in-memory stand-in for redis.asyncio.Redis, no real Redis needed."""

    def __init__(self, stop_event: asyncio.Event | None = None):
        self.streams: dict[str, list[tuple[str, dict]]] = {}
        self.groups: dict[str, set[str]] = {}
        self.acked: list[str] = []
        self.stop_event = stop_event
        self._counter = 0

    async def xgroup_create(self, name, groupname, id="0", mkstream=False):
        self.streams.setdefault(name, [])
        groups = self.groups.setdefault(name, set())
        if groupname in groups:
            raise ResponseError("BUSYGROUP Consumer Group name already exists")
        groups.add(groupname)

    async def xadd(self, name, fields):
        self._counter += 1
        message_id = f"{self._counter}-0"
        self.streams.setdefault(name, []).append((message_id, dict(fields)))
        return message_id

    async def xreadgroup(self, groupname, consumername, streams, count=10, block=5000):
        ((stream_name, _marker),) = streams.items()
        pending = self.streams.get(stream_name, [])
        if not pending:
            if self.stop_event is not None:
                self.stop_event.set()
            return []
        batch, self.streams[stream_name] = pending[:count], pending[count:]
        return [(stream_name, batch)]

    async def xack(self, name, groupname, message_id):
        self.acked.append(message_id)
        return 1


@pytest.fixture
async def db(engine) -> AsyncSession:
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


def make_registry(*extra) -> ExecutorRegistry:
    registry = ExecutorRegistry()
    registry.register(DelayExecutor())
    registry.register(ConditionExecutor())
    for executor in extra:
        registry.register(executor)
    return registry


async def _make_execution(
    db: AsyncSession,
    definition: dict,
    node_statuses: dict[str, NodeExecutionStatus],
    input_payload=None,
) -> tuple[Execution, dict[str, NodeExecution]]:
    api_key = APIKey(name="worker-test", key_hash=f"hash-{uuid.uuid4()}", is_active=True)
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
        input_payload=input_payload or {},
    )
    db.add(execution)
    await db.flush()

    nodes_by_id = {}
    for node in definition["nodes"]:
        status = node_statuses.get(node["id"], NodeExecutionStatus.PENDING)
        node_exec = NodeExecution(
            execution_id=execution.id,
            node_id=node["id"],
            node_type=node["type"],
            status=status,
            attempt=1 if status == NodeExecutionStatus.QUEUED else 0,
        )
        db.add(node_exec)
        nodes_by_id[node["id"]] = node_exec
    await db.flush()

    return execution, nodes_by_id


@pytest.mark.asyncio
async def test_worker_consumes_root_node_and_queues_downstream(db: AsyncSession):
    definition = {
        "name": "linear",
        "nodes": [
            {"id": "node1", "type": "delay", "config": {"duration_seconds": 0.01}},
            {"id": "node2", "type": "delay", "config": {"duration_seconds": 0.01}},
        ],
        "edges": [{"from": "node1", "to": "node2"}],
    }
    execution, nodes = await _make_execution(db, definition, {"node1": NodeExecutionStatus.QUEUED})

    publisher = InMemoryQueuePublisher()
    fields = serialize_job_payload(
        execution.id, nodes["node1"].id, execution.workflow_version_id, "node1", 1
    )

    await process_job(db, make_registry(), publisher, fields)

    await db.refresh(nodes["node1"])
    await db.refresh(nodes["node2"])

    assert nodes["node1"].status == NodeExecutionStatus.SUCCEEDED
    assert nodes["node1"].output_payload == {"slept_seconds": 0.01}
    assert nodes["node2"].status == NodeExecutionStatus.QUEUED
    assert len(publisher.published_jobs) == 1
    assert publisher.published_jobs[0]["node_id"] == "node2"


@pytest.mark.asyncio
async def test_downstream_and_join_waits_for_all_parents(db: AsyncSession):
    definition = {
        "name": "diamond",
        "nodes": [
            {"id": "root", "type": "delay", "config": {"duration_seconds": 0.01}},
            {"id": "left", "type": "delay", "config": {"duration_seconds": 0.01}},
            {"id": "right", "type": "delay", "config": {"duration_seconds": 0.01}},
            {"id": "join", "type": "delay", "config": {"duration_seconds": 0.01}},
        ],
        "edges": [
            {"from": "root", "to": "left"},
            {"from": "root", "to": "right"},
            {"from": "left", "to": "join"},
            {"from": "right", "to": "join"},
        ],
    }
    execution, nodes = await _make_execution(
        db,
        definition,
        {"left": NodeExecutionStatus.QUEUED, "right": NodeExecutionStatus.QUEUED},
    )
    # simulate root already succeeded before this test's scope
    nodes["root"].status = NodeExecutionStatus.SUCCEEDED
    await db.flush()

    publisher = InMemoryQueuePublisher()
    registry = make_registry()

    left_fields = serialize_job_payload(
        execution.id, nodes["left"].id, execution.workflow_version_id, "left", 1
    )
    await process_job(db, registry, publisher, left_fields)
    await db.refresh(nodes["join"])
    assert nodes["join"].status == NodeExecutionStatus.PENDING
    assert len(publisher.published_jobs) == 0

    right_fields = serialize_job_payload(
        execution.id, nodes["right"].id, execution.workflow_version_id, "right", 1
    )
    await process_job(db, registry, publisher, right_fields)
    await db.refresh(nodes["join"])
    assert nodes["join"].status == NodeExecutionStatus.QUEUED
    assert len(publisher.published_jobs) == 1
    assert publisher.published_jobs[0]["node_id"] == "join"


@pytest.mark.asyncio
async def test_condition_branch_queues_true_path_and_skips_false_path(db: AsyncSession):
    definition = {
        "name": "branching",
        "nodes": [
            {
                "id": "cond",
                "type": "condition",
                "config": {
                    "expression": "input.proceed == true",
                    "true_path": "branch-a",
                    "false_path": "branch-b",
                },
            },
            {"id": "branch-a", "type": "delay", "config": {"duration_seconds": 0.01}},
            {"id": "branch-b", "type": "delay", "config": {"duration_seconds": 0.01}},
            {"id": "descendant-b", "type": "delay", "config": {"duration_seconds": 0.01}},
        ],
        "edges": [
            {"from": "cond", "to": "branch-a"},
            {"from": "cond", "to": "branch-b"},
            {"from": "branch-b", "to": "descendant-b"},
        ],
    }
    execution, nodes = await _make_execution(
        db, definition, {"cond": NodeExecutionStatus.QUEUED}, input_payload={"proceed": True}
    )

    publisher = InMemoryQueuePublisher()
    fields = serialize_job_payload(
        execution.id, nodes["cond"].id, execution.workflow_version_id, "cond", 1
    )
    await process_job(db, make_registry(), publisher, fields)

    await db.refresh(nodes["cond"])
    await db.refresh(nodes["branch-a"])
    await db.refresh(nodes["branch-b"])
    await db.refresh(nodes["descendant-b"])

    assert nodes["cond"].status == NodeExecutionStatus.SUCCEEDED
    assert nodes["cond"].output_payload == {"result": True, "next_node": "branch-a"}
    assert nodes["branch-a"].status == NodeExecutionStatus.QUEUED
    assert nodes["branch-b"].status == NodeExecutionStatus.SKIPPED
    assert nodes["descendant-b"].status == NodeExecutionStatus.SKIPPED
    assert len(publisher.published_jobs) == 1
    assert publisher.published_jobs[0]["node_id"] == "branch-a"


@pytest.mark.asyncio
async def test_failed_executor_marks_node_failed_with_no_retry(db: AsyncSession):
    definition = {
        "name": "failing",
        "nodes": [{"id": "node1", "type": "always_fail", "config": {}}],
        "edges": [],
    }
    execution, nodes = await _make_execution(db, definition, {"node1": NodeExecutionStatus.QUEUED})

    publisher = InMemoryQueuePublisher()
    fields = serialize_job_payload(
        execution.id, nodes["node1"].id, execution.workflow_version_id, "node1", 1
    )
    await process_job(db, make_registry(FailingExecutor()), publisher, fields)

    await db.refresh(nodes["node1"])
    assert nodes["node1"].status == NodeExecutionStatus.FAILED
    assert nodes["node1"].error_message == "boom"
    assert nodes["node1"].attempt == 1

    dlq_count = len((await db.execute(select(DeadLetterJob))).scalars().all())
    assert dlq_count == 0


@pytest.mark.asyncio
async def test_terminal_duplicate_job_is_acked_without_re_execution(engine):
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as setup_session:
        definition = {
            "name": "already-done",
            "nodes": [{"id": "node1", "type": "delay", "config": {"duration_seconds": 0.01}}],
            "edges": [],
        }
        execution, nodes = await _make_execution(
            setup_session, definition, {"node1": NodeExecutionStatus.SUCCEEDED}
        )
        node_id = nodes["node1"].id
        workflow_version_id = execution.workflow_version_id
        execution_id = execution.id
        await setup_session.commit()

    stream_name = "test:eventflow:jobs"
    consumer_group = "test-eventflow-workers"
    stop_event = asyncio.Event()
    redis = FakeRedis(stop_event=stop_event)
    fields = serialize_job_payload(execution_id, node_id, workflow_version_id, "node1", 1)
    await redis.xadd(stream_name, fields)

    registry = make_registry(NeverCallExecutor())
    publisher = InMemoryQueuePublisher()

    await run_worker(
        session_factory=session_factory,
        registry=registry,
        queue_publisher=publisher,
        redis=redis,
        stream_name=stream_name,
        consumer_group=consumer_group,
        consumer_name="test-consumer",
        stop_event=stop_event,
    )

    assert len(redis.acked) == 1
    assert publisher.published_jobs == []


@pytest.mark.asyncio
async def test_ack_happens_after_state_committed(engine):
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as setup_session:
        definition = {
            "name": "ack-order",
            "nodes": [{"id": "node1", "type": "delay", "config": {"duration_seconds": 0.01}}],
            "edges": [],
        }
        execution, nodes = await _make_execution(
            setup_session, definition, {"node1": NodeExecutionStatus.QUEUED}
        )
        node_id = nodes["node1"].id
        workflow_version_id = execution.workflow_version_id
        execution_id = execution.id
        await setup_session.commit()

    stream_name = "test:eventflow:jobs"
    consumer_group = "test-eventflow-workers"
    stop_event = asyncio.Event()

    ack_saw_status = {}

    class TrackingFakeRedis(FakeRedis):
        async def xack(self, name, groupname, message_id):
            async with session_factory() as check_session:
                node = await check_session.get(NodeExecution, node_id)
                ack_saw_status["status"] = node.status
            return await super().xack(name, groupname, message_id)

    redis = TrackingFakeRedis(stop_event=stop_event)
    fields = serialize_job_payload(execution_id, node_id, workflow_version_id, "node1", 1)
    await redis.xadd(stream_name, fields)

    await run_worker(
        session_factory=session_factory,
        registry=make_registry(),
        queue_publisher=InMemoryQueuePublisher(),
        redis=redis,
        stream_name=stream_name,
        consumer_group=consumer_group,
        consumer_name="test-consumer",
        stop_event=stop_event,
    )

    assert ack_saw_status["status"] == NodeExecutionStatus.SUCCEEDED
    assert len(redis.acked) == 1
