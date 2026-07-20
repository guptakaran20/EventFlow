import asyncio
import logging
import uuid
from collections.abc import Callable

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dlq import DeadLetterJob
from app.models.enums import ExecutionStatus, NodeExecutionStatus, WorkerStatus
from app.models.execution import Execution, NodeExecution
from app.models.workflow import WorkflowVersion
from app.observability.log_helpers import (
    dead_lettered,
    node_failed,
    node_started,
    node_succeeded,
    retry_scheduled,
)
from app.queue.publisher import (
    QueuePublisher,
    RedisStreamQueuePublisher,
    deserialize_job_payload,
    serialize_job_payload,
)
from app.schemas.workflow import Node, WorkflowDefinition
from app.services.executor_registry import ExecutionContext, ExecutorRegistry, ExecutorResult
from app.services.state_transition import StateTransitionService
from app.websocket.broadcaster import broadcast_worker_updated, flush_events
from app.worker.heartbeat import HeartbeatController

logger = logging.getLogger("app.worker")

TERMINAL_NODE_STATUSES = {
    NodeExecutionStatus.SUCCEEDED,
    NodeExecutionStatus.FAILED,
    NodeExecutionStatus.SKIPPED,
    NodeExecutionStatus.DEAD_LETTERED,
}

SessionFactory = Callable[[], AsyncSession]


async def ensure_consumer_group(redis: Redis, stream_name: str, consumer_group: str) -> None:
    """Idempotently ensure the stream and consumer group exist before reading."""
    await RedisStreamQueuePublisher(redis, stream_name, consumer_group).ensure_consumer_group()


async def process_job(
    session: AsyncSession,
    registry: ExecutorRegistry,
    queue_publisher: QueuePublisher,
    fields: dict[str, str],
) -> None:
    """Run one node execution job. Commits durable state before returning."""
    job = deserialize_job_payload(fields)
    node_execution_id = job["node_execution_id"]

    node = await session.get(NodeExecution, node_execution_id)
    if node is None:
        logger.warning("node_execution %s not found, skipping", node_execution_id)
        return

    if node.status in TERMINAL_NODE_STATUSES:
        logger.info(
            "node_execution %s already terminal (%s), skipping re-execution",
            node_execution_id,
            node.status,
        )
        return

    state_service = StateTransitionService(session)
    node = await state_service.transition_node_status(
        node_execution_id=node.id,
        from_status=NodeExecutionStatus.QUEUED,
        to_status=NodeExecutionStatus.RUNNING,
    )
    node_started(session, node.execution_id, node.id, node.node_id)
    await session.commit()
    await flush_events(session)

    execution = await session.get(Execution, node.execution_id)
    version = await session.get(WorkflowVersion, execution.workflow_version_id)
    definition = WorkflowDefinition.model_validate(version.definition)
    node_def_by_id = {n.id: n for n in definition.nodes}
    node_def = node_def_by_id[node.node_id]

    all_node_execs_stmt = select(NodeExecution).where(NodeExecution.execution_id == execution.id)
    all_node_execs = (await session.execute(all_node_execs_stmt)).scalars().all()
    node_exec_by_node_id = {ne.node_id: ne for ne in all_node_execs}

    parent_ids = [e.from_node for e in definition.edges if e.to_node == node.node_id]
    upstream_outputs = {
        pid: node_exec_by_node_id[pid].output_payload
        for pid in parent_ids
        if pid in node_exec_by_node_id
    }

    executor = registry.get(node_def.type)
    context = ExecutionContext(
        execution_id=execution.id,
        node_execution_id=node.id,
        node_id=node.node_id,
        idempotency_key=f"{execution.id}:{node.node_id}:{node.attempt}",
        config=node_def.config,
        workflow_input=execution.input_payload or {},
        upstream_outputs=upstream_outputs,
        attempt=node.attempt,
    )

    try:
        result = await executor.execute(context)
    except Exception as exc:  # noqa: BLE001 - convert any executor failure into a FAILED node
        logger.exception("executor raised for node_execution %s", node.id)
        result = ExecutorResult(success=False, error=str(exc))

    # Serialize completion processing for this execution to prevent join-node race conditions.
    await session.execute(select(Execution).where(Execution.id == execution.id).with_for_update())

    # Refresh node states since other concurrent branches may have completed during our execution.
    all_node_execs_stmt = (
        select(NodeExecution)
        .where(NodeExecution.execution_id == execution.id)
        .execution_options(populate_existing=True)
    )
    all_node_execs = (await session.execute(all_node_execs_stmt)).scalars().all()
    node_exec_by_node_id = {ne.node_id: ne for ne in all_node_execs}
    node = next(ne for ne in all_node_execs if ne.id == node.id)

    if node.status != NodeExecutionStatus.RUNNING:
        logger.info(
            "Node %s is no longer RUNNING (found %s). Another worker likely completed it. Skipping.",
            node.id,
            node.status,
        )
        return

    nodes_to_publish: list[NodeExecution] = []

    if result.success:
        node.output_payload = result.output
        await state_service.transition_node_status(
            node_execution_id=node.id,
            from_status=NodeExecutionStatus.RUNNING,
            to_status=NodeExecutionStatus.SUCCEEDED,
        )
        node_succeeded(session, node.execution_id, node.id, node.node_id)
        nodes_to_publish = await _queue_downstream_nodes(
            session,
            state_service,
            execution,
            definition,
            node_def,
            node,
            node_exec_by_node_id,
            result,
        )
    else:
        node.error_message = result.error
        await state_service.transition_node_status(
            node_execution_id=node.id,
            from_status=NodeExecutionStatus.RUNNING,
            to_status=NodeExecutionStatus.FAILED,
        )
        node_failed(session, node.execution_id, node.id, node.node_id, node.error_message)
        nodes_to_publish = await _handle_node_failure(session, state_service, execution, node)

    # Check if the entire execution is complete
    all_terminal = all(ne.status in TERMINAL_NODE_STATUSES for ne in all_node_execs)
    if all_terminal and execution.status == ExecutionStatus.RUNNING:
        final_status = ExecutionStatus.SUCCEEDED
        if any(
            ne.status in {NodeExecutionStatus.FAILED, NodeExecutionStatus.DEAD_LETTERED}
            for ne in all_node_execs
        ):
            final_status = ExecutionStatus.FAILED

        await state_service.transition_execution_status(
            execution_id=execution.id,
            from_status=ExecutionStatus.RUNNING,
            to_status=final_status,
        )

    await session.commit()

    for n in nodes_to_publish:
        message_id = await queue_publisher.publish_node_execution(
            execution_id=execution.id,
            node_execution_id=n.id,
            workflow_version_id=execution.workflow_version_id,
            node_id=n.node_id,
            attempt=n.attempt,
        )
        if message_id:
            n.redis_message_id = message_id

    await session.commit()
    await flush_events(session)


async def _handle_node_failure(
    session: AsyncSession,
    state_service: StateTransitionService,
    execution: Execution,
    node: NodeExecution,
) -> list[NodeExecution]:
    """Retry the node if attempts remain, otherwise dead-letter it.

    MVP uses fixed (immediate) requeue instead of a sleeping backoff, so the
    worker never blocks a thread waiting out a delay.
    """
    if node.attempt < node.max_attempts:
        await state_service.transition_node_status(
            node_execution_id=node.id,
            from_status=NodeExecutionStatus.FAILED,
            to_status=NodeExecutionStatus.RETRYING,
        )
        retried = await state_service.transition_node_status(
            node_execution_id=node.id,
            from_status=NodeExecutionStatus.RETRYING,
            to_status=NodeExecutionStatus.QUEUED,
        )
        retry_scheduled(session, execution.id, retried.id, retried.node_id, retried.attempt)
        return [retried]

    await state_service.transition_node_status(
        node_execution_id=node.id,
        from_status=NodeExecutionStatus.FAILED,
        to_status=NodeExecutionStatus.DEAD_LETTERED,
    )
    dead_lettered(session, execution.id, node.id, node.node_id, node.error_message)
    session.add(
        DeadLetterJob(
            execution_id=execution.id,
            node_execution_id=node.id,
            redis_message_id=node.redis_message_id,
            reason=node.error_message or "max attempts exceeded",
            attempts=node.attempt,
            payload=serialize_job_payload(
                execution.id, node.id, execution.workflow_version_id, node.node_id, node.attempt
            ),
        )
    )

    if execution.status == ExecutionStatus.RUNNING:
        await state_service.transition_execution_status(
            execution_id=execution.id,
            from_status=ExecutionStatus.RUNNING,
            to_status=ExecutionStatus.FAILED,
        )

    return []


async def _queue_downstream_nodes(
    session: AsyncSession,
    state_service: StateTransitionService,
    execution: Execution,
    definition: WorkflowDefinition,
    node_def: Node,
    node: NodeExecution,
    node_exec_by_node_id: dict[str, NodeExecution],
    result: ExecutorResult,
) -> list[NodeExecution]:
    children = [e.to_node for e in definition.edges if e.from_node == node.node_id]
    if not children:
        return []

    nodes_to_publish: list[NodeExecution] = []

    # Condition nodes select exactly one branch; the other becomes SKIPPED.
    skip_ids: set[str] = set()
    if node_def.type == "condition":
        chosen = result.output.get("next_node")
        for candidate in (node_def.config.get("true_path"), node_def.config.get("false_path")):
            if candidate and candidate != chosen:
                skip_ids.add(candidate)

    # Cascade skip descendants
    queue = list(skip_ids)
    while queue:
        skip_id = queue.pop(0)
        skip_exec = node_exec_by_node_id.get(skip_id)
        if skip_exec and skip_exec.status == NodeExecutionStatus.PENDING:
            await state_service.transition_node_status(
                node_execution_id=skip_exec.id,
                from_status=NodeExecutionStatus.PENDING,
                to_status=NodeExecutionStatus.SKIPPED,
            )
            # Since our join logic requires ALL parents to be SUCCEEDED,
            # any skipped parent blocks its children.
            skipped_children = [e.to_node for e in definition.edges if e.from_node == skip_id]
            for c_id in skipped_children:
                if c_id not in queue:
                    queue.append(c_id)

    for child_id in children:
        child_exec = node_exec_by_node_id.get(child_id)
        if child_exec is None or child_exec.status != NodeExecutionStatus.PENDING:
            continue

        parent_ids = [e.from_node for e in definition.edges if e.to_node == child_id]
        all_parents_succeeded = all(
            node_exec_by_node_id[p].status == NodeExecutionStatus.SUCCEEDED for p in parent_ids
        )
        if not all_parents_succeeded:
            continue

        queued = await state_service.transition_node_status(
            node_execution_id=child_exec.id,
            from_status=NodeExecutionStatus.PENDING,
            to_status=NodeExecutionStatus.QUEUED,
        )
        nodes_to_publish.append(queued)

    return nodes_to_publish


async def run_worker(
    session_factory: SessionFactory,
    registry: ExecutorRegistry,
    queue_publisher: QueuePublisher,
    redis: Redis,
    stream_name: str,
    consumer_group: str,
    consumer_name: str,
    poll_count: int = 10,
    block_ms: int = 5000,
    stop_event: asyncio.Event | None = None,
    heartbeat: HeartbeatController | None = None,
) -> None:
    """XREADGROUP consumer loop. ACKs only after durable DB state is committed."""
    await ensure_consumer_group(redis, stream_name, consumer_group)

    if heartbeat is not None:
        await heartbeat.set_status(WorkerStatus.IDLE)

    stop = stop_event or asyncio.Event()

    while not stop.is_set():
        try:
            response = await redis.xreadgroup(
                groupname=consumer_group,
                consumername=consumer_name,
                streams={stream_name: ">"},
                count=poll_count,
                block=block_ms,
            )
        except (TimeoutError, Exception) as e:
            import redis as redis_mod

            if isinstance(e, redis_mod.exceptions.TimeoutError) or isinstance(e, TimeoutError):
                continue
            raise
        if not response:
            continue

        for _stream_name, messages in response:

            async def process_and_ack(message_id, fields):
                job = deserialize_job_payload(fields)
                current_job_id = str(job["node_execution_id"])
                execution_id = job["execution_id"]

                if heartbeat is not None:
                    # Note: When processing concurrently, the worker status will just reflect the last started job
                    await heartbeat.set_status(WorkerStatus.BUSY, current_job_id)
                    await broadcast_worker_updated(
                        execution_id,
                        heartbeat.worker_id,
                        WorkerStatus.BUSY.value,
                        current_job_id,
                    )

                async with session_factory() as session:
                    await process_job(session, registry, queue_publisher, fields)

                await redis.xack(stream_name, consumer_group, message_id)

            tasks = [process_and_ack(msg_id, fields) for msg_id, fields in messages]
            await asyncio.gather(*tasks)

            if heartbeat is not None:
                await heartbeat.set_status(WorkerStatus.IDLE)
                # Just use a dummy execution ID to broadcast the IDLE state
                await broadcast_worker_updated(
                    uuid.uuid4(), heartbeat.worker_id, WorkerStatus.IDLE.value, None
                )
