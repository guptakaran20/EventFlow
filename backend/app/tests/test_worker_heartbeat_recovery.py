import asyncio
import time
import uuid

import pytest
from redis.exceptions import ResponseError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    APIKey,
    Execution,
    ExecutionLog,
    ExecutionStatus,
    NodeExecution,
    NodeExecutionStatus,
    WorkerStatus,
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
from app.services.worker_service import WorkerService
from app.worker.heartbeat import HeartbeatController, run_heartbeat_loop
from app.worker.recovery import (
    RECOVERY_EVENT_TYPE,
    process_recovered_job,
    run_recovery_loop,
)
from app.worker.runtime import process_job, run_worker


class NeverCallExecutor:
    type = "delay"

    def validate_config(self, config: dict) -> None:
        pass

    async def execute(self, context: ExecutionContext) -> ExecutorResult:
        raise AssertionError("executor should not run for a terminal duplicate job")


class RecoveryFakeRedis:
    """In-memory Redis with pending/XPENDING/XCLAIM support."""

    def __init__(self, stop_event: asyncio.Event | None = None):
        self.streams: dict[str, list[tuple[str, dict]]] = {}
        self.groups: dict[str, set[str]] = {}
        self.pending: dict[str, dict] = {}
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
        ((stream_name, marker),) = streams.items()
        if marker != ">":
            return []
        pending_new = self.streams.get(stream_name, [])
        if not pending_new:
            if self.stop_event is not None:
                self.stop_event.set()
            return []
        batch, self.streams[stream_name] = pending_new[:count], pending_new[count:]
        now = time.monotonic()
        for message_id, fields in batch:
            self.pending[message_id] = {
                "consumer": consumername,
                "fields": fields,
                "delivered_at": now,
            }
        return [(stream_name, batch)]

    async def xack(self, name, groupname, message_id):
        self.acked.append(message_id)
        self.pending.pop(message_id, None)
        return 1

    async def xpending_range(self, name, groupname, min, max, count, consumername=None):
        now = time.monotonic()
        results = []
        for message_id, entry in self.pending.items():
            idle_ms = int((now - entry["delivered_at"]) * 1000)
            if consumername and entry["consumer"] != consumername:
                continue
            results.append(
                {
                    "message_id": message_id,
                    "consumer": entry["consumer"],
                    "time_since_delivered": idle_ms,
                    "times_delivered": 1,
                }
            )
            if len(results) >= count:
                break
        return results

    async def xclaim(self, name, groupname, consumername, min_idle_time, message_ids):
        now = time.monotonic()
        claimed = []
        for message_id in message_ids:
            entry = self.pending.get(message_id)
            if entry is None:
                continue
            idle_ms = int((now - entry["delivered_at"]) * 1000)
            if idle_ms < min_idle_time:
                continue
            entry["consumer"] = consumername
            entry["delivered_at"] = now
            claimed.append((message_id, entry["fields"]))
        return claimed

    def advance_idle(self, seconds: float) -> None:
        for entry in self.pending.values():
            entry["delivered_at"] -= seconds


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
async def test_worker_registers_on_startup(db: AsyncSession):
    service = WorkerService(db)
    worker = await service.register_worker("worker-test-1", "test-host")
    assert worker.id is not None
    assert worker.status == WorkerStatus.STARTING
    assert worker.worker_metadata["hostname"] == "test-host"

    again = await service.register_worker("worker-test-1", "test-host")
    assert again.id == worker.id


@pytest.mark.asyncio
async def test_heartbeat_updates_last_heartbeat_at(db: AsyncSession):
    service = WorkerService(db)
    worker = await service.register_worker("worker-hb", "host")
    first = worker.last_heartbeat_at

    await service.update_heartbeat(worker.id, WorkerStatus.IDLE)
    refreshed = await service.get_worker(worker.id)
    assert refreshed.last_heartbeat_at >= first


@pytest.mark.asyncio
async def test_worker_transitions_idle_busy_idle(db: AsyncSession):
    service = WorkerService(db)
    worker = await service.register_worker("worker-trans", "host")
    controller = HeartbeatController(worker.id)

    await controller.set_status(WorkerStatus.IDLE)
    await service.update_heartbeat(worker.id, WorkerStatus.IDLE)
    w = await service.get_worker(worker.id)
    assert w.status == WorkerStatus.IDLE

    await controller.set_status(WorkerStatus.BUSY, "job-123")
    await service.update_heartbeat(worker.id, WorkerStatus.BUSY, "job-123")
    w = await service.get_worker(worker.id)
    assert w.status == WorkerStatus.BUSY
    assert w.current_job_id == "job-123"

    await controller.set_status(WorkerStatus.IDLE)
    await service.update_heartbeat(worker.id, WorkerStatus.IDLE)
    w = await service.get_worker(worker.id)
    assert w.status == WorkerStatus.IDLE
    assert w.current_job_id is None


@pytest.mark.asyncio
async def test_shutdown_marks_worker_offline(db: AsyncSession):
    service = WorkerService(db)
    worker = await service.register_worker("worker-off", "host")
    await service.mark_offline(worker.id)
    w = await service.get_worker(worker.id)
    assert w.status == WorkerStatus.OFFLINE
    assert w.current_job_id is None


@pytest.mark.asyncio
async def test_stale_pending_message_detected():
    redis = RecoveryFakeRedis()
    stream = "test:jobs"
    group = "test-group"
    await redis.xgroup_create(stream, group, mkstream=True)
    await redis.xadd(stream, {"k": "v"})
    await redis.xreadgroup(group, "dead-worker", {stream: ">"}, count=1)
    redis.advance_idle(700)
    pending = await redis.xpending_range(stream, group, "-", "+", 10)
    assert len(pending) == 1
    assert pending[0]["time_since_delivered"] >= 600_000


@pytest.mark.asyncio
async def test_xclaim_transfers_ownership():
    redis = RecoveryFakeRedis()
    stream = "test:jobs"
    group = "test-group"
    await redis.xgroup_create(stream, group, mkstream=True)
    msg_id = await redis.xadd(stream, {"k": "v"})
    await redis.xreadgroup(group, "dead-worker", {stream: ">"}, count=1)
    redis.advance_idle(700)
    claimed = await redis.xclaim(stream, group, "recovery-worker", 600_000, [msg_id])
    assert len(claimed) == 1
    assert claimed[0][0] == msg_id
    pending = await redis.xpending_range(stream, group, "-", "+", 10)
    assert pending[0]["consumer"] == "recovery-worker"


@pytest.mark.asyncio
async def test_claimed_job_executes_normally(db: AsyncSession):
    definition = {
        "name": "recover-run",
        "nodes": [{"id": "node1", "type": "delay", "config": {"duration_seconds": 0.01}}],
        "edges": [],
    }
    execution, nodes = await _make_execution(db, definition, {"node1": NodeExecutionStatus.QUEUED})
    fields = serialize_job_payload(
        execution.id, nodes["node1"].id, execution.workflow_version_id, "node1", 1
    )

    executed = await process_recovered_job(
        db,
        make_registry(),
        InMemoryQueuePublisher(),
        fields,
        "1-0",
        "dead-worker",
        "recovery-worker",
    )
    assert executed is True
    await db.refresh(nodes["node1"])
    assert nodes["node1"].status == NodeExecutionStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_succeeded_stale_job_acked_without_execution(db: AsyncSession):
    definition = {
        "name": "recover-skip",
        "nodes": [{"id": "node1", "type": "delay", "config": {"duration_seconds": 0.01}}],
        "edges": [],
    }
    execution, nodes = await _make_execution(
        db, definition, {"node1": NodeExecutionStatus.SUCCEEDED}
    )
    fields = serialize_job_payload(
        execution.id, nodes["node1"].id, execution.workflow_version_id, "node1", 1
    )

    executed = await process_recovered_job(
        db,
        make_registry(NeverCallExecutor()),
        InMemoryQueuePublisher(),
        fields,
        "1-0",
        "dead-worker",
        "recovery-worker",
    )
    assert executed is False
    await db.refresh(nodes["node1"])
    assert nodes["node1"].status == NodeExecutionStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_dead_lettered_stale_job_acked_without_execution(db: AsyncSession):
    definition = {
        "name": "recover-dlq",
        "nodes": [{"id": "node1", "type": "delay", "config": {"duration_seconds": 0.01}}],
        "edges": [],
    }
    execution, nodes = await _make_execution(
        db, definition, {"node1": NodeExecutionStatus.DEAD_LETTERED}
    )
    fields = serialize_job_payload(
        execution.id, nodes["node1"].id, execution.workflow_version_id, "node1", 1
    )

    executed = await process_recovered_job(
        db,
        make_registry(NeverCallExecutor()),
        InMemoryQueuePublisher(),
        fields,
        "2-0",
        "dead-worker",
        "recovery-worker",
    )
    assert executed is False


@pytest.mark.asyncio
async def test_recovery_respects_postgresql_as_source_of_truth(db: AsyncSession):
    definition = {
        "name": "recover-truth",
        "nodes": [{"id": "node1", "type": "delay", "config": {"duration_seconds": 0.01}}],
        "edges": [],
    }
    execution, nodes = await _make_execution(
        db, definition, {"node1": NodeExecutionStatus.SUCCEEDED}
    )
    fields = serialize_job_payload(
        execution.id, nodes["node1"].id, execution.workflow_version_id, "node1", 1
    )
    publisher = InMemoryQueuePublisher()

    await process_recovered_job(
        db, make_registry(NeverCallExecutor()), publisher, fields, "3-0", "w1", "w2"
    )
    assert publisher.published_jobs == []
    await db.refresh(nodes["node1"])
    assert nodes["node1"].status == NodeExecutionStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_recovery_writes_execution_log(db: AsyncSession):
    definition = {
        "name": "recover-log",
        "nodes": [{"id": "node1", "type": "delay", "config": {"duration_seconds": 0.01}}],
        "edges": [],
    }
    execution, nodes = await _make_execution(
        db, definition, {"node1": NodeExecutionStatus.SUCCEEDED}
    )
    fields = serialize_job_payload(
        execution.id, nodes["node1"].id, execution.workflow_version_id, "node1", 1
    )

    await process_recovered_job(
        db,
        make_registry(NeverCallExecutor()),
        InMemoryQueuePublisher(),
        fields,
        "4-0",
        "prev-worker",
        "claim-worker",
    )

    stmt = select(ExecutionLog).where(ExecutionLog.node_execution_id == nodes["node1"].id)
    logs = (await db.execute(stmt)).scalars().all()
    assert len(logs) == 1
    log = logs[0]
    assert log.event_type == RECOVERY_EVENT_TYPE
    assert log.log_metadata["previous_worker"] == "prev-worker"
    assert log.log_metadata["claiming_worker"] == "claim-worker"
    assert log.log_metadata["redis_message_id"] == "4-0"


@pytest.mark.asyncio
async def test_heartbeat_loop_does_not_block_worker_execution(engine):
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        worker = await WorkerService(session).register_worker("hb-loop", "host")

    controller = HeartbeatController(worker.id)
    stop = asyncio.Event()
    hb_task = asyncio.create_task(run_heartbeat_loop(session_factory, controller, 0.05, stop))

    definition = {
        "name": "hb-block",
        "nodes": [{"id": "node1", "type": "delay", "config": {"duration_seconds": 0.05}}],
        "edges": [],
    }
    async with session_factory() as setup:
        execution, nodes = await _make_execution(
            setup, definition, {"node1": NodeExecutionStatus.QUEUED}
        )
        fields = serialize_job_payload(
            execution.id, nodes["node1"].id, execution.workflow_version_id, "node1", 1
        )
        await setup.commit()

    async with session_factory() as session:
        await process_job(session, make_registry(), InMemoryQueuePublisher(), fields)

    await asyncio.sleep(0.15)
    async with session_factory() as session:
        refreshed = await WorkerService(session).get_worker(worker.id)
        assert refreshed.last_heartbeat_at is not None

    stop.set()
    await hb_task


@pytest.mark.asyncio
async def test_recovery_loop_claims_and_acks_stale_job(engine):
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as setup:
        definition = {
            "name": "recovery-loop",
            "nodes": [{"id": "node1", "type": "delay", "config": {"duration_seconds": 0.01}}],
            "edges": [],
        }
        execution, nodes = await _make_execution(
            setup, definition, {"node1": NodeExecutionStatus.QUEUED}
        )
        fields = serialize_job_payload(
            execution.id, nodes["node1"].id, execution.workflow_version_id, "node1", 1
        )
        node_id = nodes["node1"].id
        await setup.commit()

    stream = "test:recovery"
    group = "test-group"
    redis = RecoveryFakeRedis()
    msg_id = await redis.xadd(stream, fields)
    await redis.xgroup_create(stream, group, mkstream=True)
    await redis.xreadgroup(group, "dead-worker", {stream: ">"}, count=1)
    redis.advance_idle(2)

    stop = asyncio.Event()
    recovery_task = asyncio.create_task(
        run_recovery_loop(
            session_factory,
            make_registry(),
            InMemoryQueuePublisher(),
            redis,
            stream,
            group,
            "recovery-worker",
            idle_timeout_seconds=1.0,
            poll_interval_seconds=0.1,
            stop_event=stop,
        )
    )

    await asyncio.sleep(0.5)
    stop.set()
    await recovery_task

    assert msg_id in redis.acked
    async with session_factory() as session:
        node = await session.get(NodeExecution, node_id)
        assert node.status == NodeExecutionStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_run_worker_with_heartbeat_lifecycle(engine):
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as setup:
        worker = await WorkerService(setup).register_worker("lifecycle-worker", "host")
        worker_id = worker.id
        definition = {
            "name": "lifecycle",
            "nodes": [{"id": "node1", "type": "delay", "config": {"duration_seconds": 0.01}}],
            "edges": [],
        }
        execution, nodes = await _make_execution(
            setup, definition, {"node1": NodeExecutionStatus.QUEUED}
        )
        fields = serialize_job_payload(
            execution.id, nodes["node1"].id, execution.workflow_version_id, "node1", 1
        )
        node_id = nodes["node1"].id
        await setup.commit()

    stream = "test:lifecycle"
    group = "test-group"
    stop = asyncio.Event()
    redis = RecoveryFakeRedis(stop_event=stop)
    await redis.xadd(stream, fields)

    controller = HeartbeatController(worker_id)
    await controller.set_status(WorkerStatus.IDLE)

    await run_worker(
        session_factory=session_factory,
        registry=make_registry(),
        queue_publisher=InMemoryQueuePublisher(),
        redis=redis,
        stream_name=stream,
        consumer_group=group,
        consumer_name="lifecycle-worker",
        stop_event=stop,
        heartbeat=controller,
    )

    async with session_factory() as session:
        node = await session.get(NodeExecution, node_id)
        assert node.status == NodeExecutionStatus.SUCCEEDED
        assert len(redis.acked) == 1
