import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.session import get_db_session
from app.models.enums import WorkerStatus
from app.models.worker import Worker


class WorkerService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def register_worker(self, worker_name: str, hostname: str) -> Worker:
        """Upsert worker row on startup. Reuses existing row for the same worker_name."""
        stmt = select(Worker).where(Worker.worker_name == worker_name)
        result = await self._db.execute(stmt)
        worker = result.scalar_one_or_none()

        now = datetime.now(UTC)
        if worker is None:
            worker = Worker(
                worker_name=worker_name,
                status=WorkerStatus.STARTING,
                last_heartbeat_at=now,
                worker_metadata={"hostname": hostname},
            )
            self._db.add(worker)
        else:
            worker.status = WorkerStatus.STARTING
            worker.last_heartbeat_at = now
            worker.current_job_id = None
            metadata = dict(worker.worker_metadata or {})
            metadata["hostname"] = hostname
            worker.worker_metadata = metadata

        await self._db.commit()
        await self._db.refresh(worker)
        return worker

    async def update_heartbeat(
        self,
        worker_id: uuid.UUID,
        status: WorkerStatus,
        current_job_id: str | None = None,
    ) -> None:
        worker = await self._db.get(Worker, worker_id)
        if worker is None:
            return
        worker.status = status
        worker.last_heartbeat_at = datetime.now(UTC)
        worker.current_job_id = current_job_id
        await self._db.commit()

    async def mark_offline(self, worker_id: uuid.UUID) -> None:
        worker = await self._db.get(Worker, worker_id)
        if worker is None:
            return
        worker.status = WorkerStatus.OFFLINE
        worker.current_job_id = None
        worker.last_heartbeat_at = datetime.now(UTC)
        await self._db.commit()

    async def list_workers(self, limit: int = 50, offset: int = 0) -> list[Worker]:
        stmt = (
            select(Worker)
            .order_by(Worker.last_heartbeat_at.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_worker(self, worker_id: uuid.UUID) -> Worker | None:
        return await self._db.get(Worker, worker_id)

    async def require_worker(self, worker_id: uuid.UUID) -> Worker:
        worker = await self.get_worker(worker_id)
        if worker is None:
            raise AppError("Worker not found", code="not_found", status_code=404)
        return worker


async def get_worker_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkerService:
    return WorkerService(db)
