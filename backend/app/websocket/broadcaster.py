"""Safe broadcast helpers used by the engine, worker runtime, and recovery.

Every function here catches and logs its own errors. Broadcasting is
notification-only and must NEVER fail or roll back a committed database state
transition, so callers can invoke these without a try/except of their own.

Call these only AFTER ``session.commit()`` so clients never observe state that
is not yet durable.
"""

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.websocket import events
from app.websocket.connection_manager import get_connection_manager

logger = logging.getLogger("app.websocket.broadcaster")

_SESSION_EVENTS_KEY = "ws_events"


def stage_event(session: AsyncSession, envelope: dict[str, Any]) -> None:
    """Buffer an envelope on the session to be emitted after commit.

    Buffering (rather than broadcasting inline) guarantees events are only sent
    for durably committed state and preserves per-execution ordering.
    """
    session.info.setdefault(_SESSION_EVENTS_KEY, []).append(envelope)


async def flush_events(session: AsyncSession) -> None:
    """Broadcast and clear all events staged on the session. Never raises."""
    staged: list[dict[str, Any]] = session.info.pop(_SESSION_EVENTS_KEY, [])
    await broadcast_envelopes(staged)


async def _safe_broadcast(execution_id: uuid.UUID | str, message: dict[str, Any]) -> None:
    try:
        await get_connection_manager().broadcast(str(execution_id), message)
    except Exception:
        logger.exception("websocket broadcast failed for execution %s", execution_id)


async def broadcast_envelopes(messages: list[dict[str, Any]]) -> None:
    """Emit a batch of pre-built envelopes in order, after DB commit.

    Each envelope carries its own ``execution_id``. Envelopes without one are
    skipped. Never raises.
    """
    for message in messages:
        execution_id = message.get("execution_id")
        if execution_id is None:
            continue
        await _safe_broadcast(execution_id, message)


async def broadcast_execution_updated(execution_id: uuid.UUID | str, status: str) -> None:
    await _safe_broadcast(execution_id, events.execution_updated(execution_id, status))


async def broadcast_node_updated(
    execution_id: uuid.UUID | str,
    node_execution_id: uuid.UUID | str,
    node_id: str,
    status: str,
    attempt: int,
) -> None:
    await _safe_broadcast(
        execution_id,
        events.node_updated(execution_id, node_execution_id, node_id, status, attempt),
    )


async def broadcast_execution_log(
    execution_id: uuid.UUID | str,
    level: str,
    event_type: str,
    message: str,
    node_execution_id: uuid.UUID | str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    await _safe_broadcast(
        execution_id,
        events.execution_log(execution_id, level, event_type, message, node_execution_id, metadata),
    )


async def broadcast_worker_updated(
    execution_id: uuid.UUID | str | None,
    worker_id: uuid.UUID | str,
    status: str,
    current_job_id: str | None = None,
) -> None:
    if execution_id is None:
        return
    await _safe_broadcast(
        execution_id,
        events.worker_updated(execution_id, worker_id, status, current_job_id),
    )
