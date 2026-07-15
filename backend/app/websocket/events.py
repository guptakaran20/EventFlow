"""WebSocket event envelope builders.

All messages share one envelope shape::

    {"type": ..., "execution_id": ..., "timestamp": <iso8601>, "data": {...}}

Timestamps are produced at build time to reflect committed state.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

EVENT_EXECUTION_UPDATED = "execution_updated"
EVENT_NODE_UPDATED = "node_updated"
EVENT_EXECUTION_LOG = "execution_log"
EVENT_WORKER_UPDATED = "worker_updated"
EVENT_PING = "ping"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _envelope(
    event_type: str, execution_id: uuid.UUID | str | None, data: dict[str, Any]
) -> dict[str, Any]:
    return {
        "type": event_type,
        "execution_id": str(execution_id) if execution_id is not None else None,
        "timestamp": _now_iso(),
        "data": data,
    }


def execution_updated(execution_id: uuid.UUID | str, status: str) -> dict[str, Any]:
    return _envelope(EVENT_EXECUTION_UPDATED, execution_id, {"status": status})


def node_updated(
    execution_id: uuid.UUID | str,
    node_execution_id: uuid.UUID | str,
    node_id: str,
    status: str,
    attempt: int,
) -> dict[str, Any]:
    return _envelope(
        EVENT_NODE_UPDATED,
        execution_id,
        {
            "node_execution_id": str(node_execution_id),
            "node_id": node_id,
            "status": status,
            "attempt": attempt,
        },
    )


def execution_log(
    execution_id: uuid.UUID | str,
    level: str,
    event_type: str,
    message: str,
    node_execution_id: uuid.UUID | str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _envelope(
        EVENT_EXECUTION_LOG,
        execution_id,
        {
            "node_execution_id": str(node_execution_id) if node_execution_id else None,
            "level": level,
            "event_type": event_type,
            "message": message,
            "metadata": metadata,
        },
    )


def worker_updated(
    execution_id: uuid.UUID | str | None,
    worker_id: uuid.UUID | str,
    status: str,
    current_job_id: str | None = None,
) -> dict[str, Any]:
    return _envelope(
        EVENT_WORKER_UPDATED,
        execution_id,
        {
            "worker_id": str(worker_id),
            "status": status,
            "current_job_id": current_job_id,
        },
    )


def ping() -> dict[str, Any]:
    return _envelope(EVENT_PING, None, {})
