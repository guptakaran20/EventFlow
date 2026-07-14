"""Worker heartbeat loop — runs in a background task, never blocks job execution."""

import asyncio
import logging
import uuid
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import WorkerStatus
from app.services.worker_service import WorkerService

logger = logging.getLogger("app.worker.heartbeat")

SessionFactory = Callable[[], AsyncSession]


class HeartbeatController:
    """Tracks live worker status for heartbeat updates."""

    def __init__(self, worker_id: uuid.UUID):
        self.worker_id = worker_id
        self._status = WorkerStatus.STARTING
        self._current_job_id: str | None = None
        self._lock = asyncio.Lock()

    async def set_status(self, status: WorkerStatus, current_job_id: str | None = None) -> None:
        async with self._lock:
            self._status = status
            if current_job_id is not None:
                self._current_job_id = current_job_id
            elif status != WorkerStatus.BUSY:
                self._current_job_id = None

    async def snapshot(self) -> tuple[WorkerStatus, str | None]:
        async with self._lock:
            return self._status, self._current_job_id


async def run_heartbeat_loop(
    session_factory: SessionFactory,
    controller: HeartbeatController,
    interval_seconds: float,
    stop_event: asyncio.Event,
) -> None:
    """Periodically persist worker heartbeat without blocking the consumer loop."""
    while not stop_event.is_set():
        try:
            status, current_job_id = await controller.snapshot()
            async with session_factory() as session:
                await WorkerService(session).update_heartbeat(
                    controller.worker_id, status, current_job_id
                )
        except Exception:
            logger.exception("heartbeat update failed for worker %s", controller.worker_id)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            break
        except TimeoutError:
            continue
