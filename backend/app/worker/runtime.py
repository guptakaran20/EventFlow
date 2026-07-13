import asyncio
import logging
from collections.abc import Callable

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NodeExecutionStatus
from app.models.execution import Execution, NodeExecution
from app.models.workflow import WorkflowVersion
from app.queue.publisher import QueuePublisher, RedisStreamQueuePublisher, deserialize_job_payload
from app.schemas.workflow import Node, WorkflowDefinition
from app.services.executor_registry import ExecutionContext, ExecutorRegistry, ExecutorResult
from app.services.state_transition import StateTransitionService

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
    await session.commit()

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

    if result.success:
        node.output_payload = result.output
        await state_service.transition_node_status(
            node_execution_id=node.id,
            from_status=NodeExecutionStatus.RUNNING,
            to_status=NodeExecutionStatus.SUCCEEDED,
        )
        await _queue_downstream_nodes(
            session,
            state_service,
            queue_publisher,
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

    await session.commit()


async def _queue_downstream_nodes(
    session: AsyncSession,
    state_service: StateTransitionService,
    queue_publisher: QueuePublisher,
    execution: Execution,
    definition: WorkflowDefinition,
    node_def: Node,
    node: NodeExecution,
    node_exec_by_node_id: dict[str, NodeExecution],
    result: ExecutorResult,
) -> None:
    children = [e.to_node for e in definition.edges if e.from_node == node.node_id]
    if not children:
        return

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
        message_id = await queue_publisher.publish_node_execution(
            execution_id=execution.id,
            node_execution_id=queued.id,
            workflow_version_id=execution.workflow_version_id,
            node_id=queued.node_id,
            attempt=queued.attempt,
        )
        if message_id:
            queued.redis_message_id = message_id


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
) -> None:
    """XREADGROUP consumer loop. ACKs only after durable DB state is committed."""
    await ensure_consumer_group(redis, stream_name, consumer_group)

    while stop_event is None or not stop_event.is_set():
        response = await redis.xreadgroup(
            groupname=consumer_group,
            consumername=consumer_name,
            streams={stream_name: ">"},
            count=poll_count,
            block=block_ms,
        )
        if not response:
            continue

        for _stream_name, messages in response:
            for message_id, fields in messages:
                async with session_factory() as session:
                    await process_job(session, registry, queue_publisher, fields)
                await redis.xack(stream_name, consumer_group, message_id)
