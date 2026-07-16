"""WebSocket endpoint for live execution updates.

Reuses the existing API key mechanism (via the ``api_key`` query parameter,
since browsers cannot set custom headers on WebSocket handshakes) and enforces
execution ownership before accepting the connection.
"""

import asyncio
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import get_current_principal_from_token, resolve_api_key_id
from app.db.session import get_session_factory
from app.models.execution import Execution
from app.models.workflow import Workflow
from app.websocket import events
from app.websocket.connection_manager import get_connection_manager

logger = logging.getLogger("app.websocket.endpoint")

router = APIRouter(prefix="/api/v1/ws", tags=["websocket"])


async def _authorize(execution_id: uuid.UUID, token: str | None) -> bool:
    """Return True when ``token`` is valid and owns ``execution_id``."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            principal = await get_current_principal_from_token(token)
            owner_id = await resolve_api_key_id(principal, session)
        except AppError:
            return False

        stmt = (
            select(Execution.id)
            .join(Workflow, Workflow.id == Execution.workflow_id)
            .where(Execution.id == execution_id, Workflow.owner_api_key_id == owner_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None


@router.websocket("/executions/{execution_id}")
async def execution_updates(websocket: WebSocket, execution_id: uuid.UUID) -> None:
    token = websocket.query_params.get("token")

    if not await _authorize(execution_id, token):
        # 1008 = policy violation. Reject BEFORE accept for unauthorized clients.
        await websocket.close(code=1008)
        return

    try:
        await websocket.accept()
    except RuntimeError:
        # Client likely disconnected before accept could complete (e.g. React Strict Mode)
        return

    manager = get_connection_manager()
    execution_key = str(execution_id)
    await manager.connect(execution_key, websocket)

    heartbeat_task = asyncio.create_task(_heartbeat(websocket))
    try:
        # Notification-only: we don't process client input, just keep the socket
        # open and detect disconnects. Any inbound frame is ignored.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning("websocket receive loop error for execution %s", execution_key)
    finally:
        heartbeat_task.cancel()
        await manager.disconnect(execution_key, websocket)


async def _heartbeat(websocket: WebSocket) -> None:
    """Periodically ping the client so dead sockets surface and get cleaned up."""
    interval = get_settings().websocket_heartbeat_interval_seconds
    try:
        while True:
            await asyncio.sleep(interval)
            await websocket.send_json(events.ping())
    except asyncio.CancelledError:
        raise
    except Exception:
        # A failed ping means the socket is dead; ending the task lets the
        # receive loop's disconnect handling clean up the connection.
        return
