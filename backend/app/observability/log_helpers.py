"""Structured `ExecutionLog` creation helpers.

Each helper builds and stages (`session.add`) one `ExecutionLog` row. Callers
are responsible for committing (state transitions already commit around
these calls), keeping helpers cheap and side-effect-free beyond staging.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import LogLevel
from app.models.log import ExecutionLog

EVENT_EXECUTION_STARTED = "execution_started"
EVENT_NODE_STARTED = "node_started"
EVENT_NODE_SUCCEEDED = "node_succeeded"
EVENT_NODE_FAILED = "node_failed"
EVENT_RETRY_SCHEDULED = "retry_scheduled"
EVENT_DEAD_LETTERED = "dead_lettered"
EVENT_WORKER_RECOVERED_JOB = "job_recovered"


def _add_log(
    session: AsyncSession,
    execution_id: uuid.UUID,
    node_execution_id: uuid.UUID | None,
    level: LogLevel,
    event_type: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> ExecutionLog:
    log = ExecutionLog(
        execution_id=execution_id,
        node_execution_id=node_execution_id,
        level=level,
        event_type=event_type,
        message=message,
        log_metadata=metadata,
    )
    session.add(log)
    return log


def execution_started(session: AsyncSession, execution_id: uuid.UUID) -> ExecutionLog:
    return _add_log(
        session, execution_id, None, LogLevel.INFO, EVENT_EXECUTION_STARTED, "Execution started"
    )


def node_started(
    session: AsyncSession, execution_id: uuid.UUID, node_execution_id: uuid.UUID, node_id: str
) -> ExecutionLog:
    return _add_log(
        session,
        execution_id,
        node_execution_id,
        LogLevel.INFO,
        EVENT_NODE_STARTED,
        f"Node {node_id} started",
        {"node_id": node_id},
    )


def node_succeeded(
    session: AsyncSession, execution_id: uuid.UUID, node_execution_id: uuid.UUID, node_id: str
) -> ExecutionLog:
    return _add_log(
        session,
        execution_id,
        node_execution_id,
        LogLevel.INFO,
        EVENT_NODE_SUCCEEDED,
        f"Node {node_id} succeeded",
        {"node_id": node_id},
    )


def node_failed(
    session: AsyncSession,
    execution_id: uuid.UUID,
    node_execution_id: uuid.UUID,
    node_id: str,
    error: str | None,
) -> ExecutionLog:
    return _add_log(
        session,
        execution_id,
        node_execution_id,
        LogLevel.ERROR,
        EVENT_NODE_FAILED,
        f"Node {node_id} failed",
        {"node_id": node_id, "error": error},
    )


def retry_scheduled(
    session: AsyncSession,
    execution_id: uuid.UUID,
    node_execution_id: uuid.UUID,
    node_id: str,
    attempt: int,
) -> ExecutionLog:
    return _add_log(
        session,
        execution_id,
        node_execution_id,
        LogLevel.WARNING,
        EVENT_RETRY_SCHEDULED,
        f"Node {node_id} retry scheduled (attempt {attempt})",
        {"node_id": node_id, "attempt": attempt},
    )


def dead_lettered(
    session: AsyncSession,
    execution_id: uuid.UUID,
    node_execution_id: uuid.UUID,
    node_id: str,
    reason: str | None,
) -> ExecutionLog:
    return _add_log(
        session,
        execution_id,
        node_execution_id,
        LogLevel.ERROR,
        EVENT_DEAD_LETTERED,
        f"Node {node_id} dead-lettered",
        {"node_id": node_id, "reason": reason},
    )


def worker_recovered_job(
    session: AsyncSession,
    execution_id: uuid.UUID,
    node_execution_id: uuid.UUID,
    redis_message_id: str,
    previous_worker: str | None,
    claiming_worker: str,
    reason: str,
) -> ExecutionLog:
    return _add_log(
        session,
        execution_id,
        node_execution_id,
        LogLevel.INFO,
        EVENT_WORKER_RECOVERED_JOB,
        "Stale pending job reclaimed",
        {
            "previous_worker": previous_worker,
            "claiming_worker": claiming_worker,
            "redis_message_id": redis_message_id,
            "recovery_reason": reason,
        },
    )
