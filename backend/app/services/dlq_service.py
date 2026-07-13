import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.session import get_db_session
from app.models.dlq import DeadLetterJob
from app.models.execution import Execution
from app.models.workflow import Workflow


class DlqService:
    def __init__(self, db: AsyncSession):
        self._db = db

    def _owned_stmt(self, owner_api_key_id: uuid.UUID):
        return (
            select(DeadLetterJob)
            .join(Execution, Execution.id == DeadLetterJob.execution_id)
            .join(Workflow, Workflow.id == Execution.workflow_id)
            .where(Workflow.owner_api_key_id == owner_api_key_id)
        )

    async def list_dlq_jobs(
        self, owner_api_key_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[DeadLetterJob]:
        stmt = (
            self._owned_stmt(owner_api_key_id)
            .order_by(DeadLetterJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_dlq_job(
        self, dlq_id: uuid.UUID, owner_api_key_id: uuid.UUID
    ) -> DeadLetterJob | None:
        stmt = self._owned_stmt(owner_api_key_id).where(DeadLetterJob.id == dlq_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def resolve_dlq_job(
        self, dlq_id: uuid.UUID, owner_api_key_id: uuid.UUID, resolution_note: str | None
    ) -> DeadLetterJob:
        job = await self.get_dlq_job(dlq_id, owner_api_key_id)
        if job is None:
            raise AppError("Dead letter job not found", code="not_found", status_code=404)

        job.resolved_at = datetime.now(UTC)
        job.resolution_note = resolution_note
        await self._db.commit()
        await self._db.refresh(job)
        return job


async def get_dlq_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> DlqService:
    return DlqService(db)
