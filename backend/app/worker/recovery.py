"""Stale pending job recovery via XPENDING / XCLAIM."""

import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import LogLevel, NodeExecutionStatus
from app.models.log import ExecutionLog
from app.queue.publisher import QueuePublisher, deserialize_job_payload
from app.services.executor_registry import ExecutorRegistry
from app.worker.runtime import TERMINAL_NODE_STATUSES, process_job

logger = logging.getLogger("app.worker.recovery")

SessionFactory = Callable[[], AsyncSession]

RECOVERY_EVENT_TYPE = "job_recovered"
RECOVERY_REASON_IDLE = "pending_idle_timeout_exceeded"


async def log_recovery_event(
    session: AsyncSession,
    execution_id: uuid.UUID,
    node_execution_id: uuid.UUID,
    redis_message_id: str,
    previous_worker: str | None,
    claiming_worker: str,
    recovery_reason: str,
) -> None:
    session.add(
        ExecutionLog(
            execution_id=execution_id,
            node_execution_id=node_execution_id,
            level=LogLevel.INFO,
            event_type=RECOVERY_EVENT_TYPE,
            message="Stale pending job reclaimed",
            log_metadata={
                "previous_worker": previous_worker,
                "claiming_worker": claiming_worker,
                "redis_message_id": redis_message_id,
                "recovery_reason": recovery_reason,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
    )


async def process_recovered_job(
    session: AsyncSession,
    registry: ExecutorRegistry,
    queue_publisher: QueuePublisher,
    fields: dict[str, str],
    redis_message_id: str,
    previous_worker: str | None,
    claiming_worker: str,
) -> bool:
    """Handle a claimed stale job. Returns True if the job was executed (not terminal skip)."""
    job = deserialize_job_payload(fields)
    node_execution_id = job["node_execution_id"]

    from app.models.execution import NodeExecution

    node = await session.get(NodeExecution, node_execution_id)
    if node is None:
        logger.warning("recovered node_execution %s not found", node_execution_id)
        return False

    await log_recovery_event(
        session,
        execution_id=job["execution_id"],
        node_execution_id=node_execution_id,
        redis_message_id=redis_message_id,
        previous_worker=previous_worker,
        claiming_worker=claiming_worker,
        recovery_reason=RECOVERY_REASON_IDLE,
    )
    if node.status in TERMINAL_NODE_STATUSES:
        logger.info(
            "recovered job %s already terminal (%s), ACK without execution",
            node_execution_id,
            node.status,
        )
        await session.commit()
        return False

    if node.status == NodeExecutionStatus.RUNNING:

        # Note: we manually override the transition rule since RUNNING->QUEUED isn't standard
        node.status = NodeExecutionStatus.QUEUED
        logger.info("reverted recovered job %s from RUNNING to QUEUED", node_execution_id)

    await session.commit()
    await process_job(session, registry, queue_publisher, fields)
    return True


async def _claim_stale_pending(
    redis: Redis,
    stream_name: str,
    consumer_group: str,
    consumer_name: str,
    idle_timeout_ms: int,
    batch_size: int = 10,
) -> list[tuple[str, dict[str, str], str | None]]:
    """Return claimed (message_id, fields, previous_consumer) tuples."""
    pending = await redis.xpending_range(
        name=stream_name,
        groupname=consumer_group,
        min="-",
        max="+",
        count=batch_size,
    )
    if not pending:
        return []

    stale_ids: list[str] = []
    previous_by_id: dict[str, str | None] = {}
    for entry in pending:
        message_id = entry["message_id"]
        idle_ms = entry["time_since_delivered"]
        if idle_ms >= idle_timeout_ms:
            stale_ids.append(message_id)
            previous_by_id[message_id] = entry.get("consumer")

    if not stale_ids:
        return []

    claimed = await redis.xclaim(
        name=stream_name,
        groupname=consumer_group,
        consumername=consumer_name,
        min_idle_time=idle_timeout_ms,
        message_ids=stale_ids,
    )
    results: list[tuple[str, dict[str, str], str | None]] = []
    for message_id, fields in claimed:
        results.append((message_id, fields, previous_by_id.get(message_id)))
    return results


async def run_recovery_loop(
    session_factory: SessionFactory,
    registry: ExecutorRegistry,
    queue_publisher: QueuePublisher,
    redis: Redis,
    stream_name: str,
    consumer_group: str,
    consumer_name: str,
    idle_timeout_seconds: float,
    poll_interval_seconds: float,
    stop_event: asyncio.Event,
) -> None:
    """Periodically inspect XPENDING and reclaim stale jobs via XCLAIM."""
    idle_timeout_ms = int(idle_timeout_seconds * 1000)

    while not stop_event.is_set():
        try:
            claimed_jobs = await _claim_stale_pending(
                redis,
                stream_name,
                consumer_group,
                consumer_name,
                idle_timeout_ms,
            )
            for message_id, fields, previous_worker in claimed_jobs:
                async with session_factory() as session:
                    await process_recovered_job(
                        session,
                        registry,
                        queue_publisher,
                        fields,
                        message_id,
                        previous_worker,
                        consumer_name,
                    )
                await redis.xack(stream_name, consumer_group, message_id)
        except Exception:
            logger.exception("recovery loop error")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval_seconds)
            break
        except TimeoutError:
            continue
