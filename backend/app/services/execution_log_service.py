import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.session import get_db_session
from app.models.execution import Execution
from app.models.log import ExecutionLog
from app.models.workflow import Workflow


class ExecutionLogService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def _check_ownership(self, execution_id: uuid.UUID, owner_api_key_id: uuid.UUID) -> None:
        stmt = (
            select(Execution.id)
            .join(Workflow, Workflow.id == Execution.workflow_id)
            .where(Execution.id == execution_id, Workflow.owner_api_key_id == owner_api_key_id)
        )
        result = await self._db.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise AppError("Execution not found", code="not_found", status_code=404)

    async def list_logs(
        self,
        execution_id: uuid.UUID,
        owner_api_key_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ExecutionLog]:
        await self._check_ownership(execution_id, owner_api_key_id)

        stmt = (
            select(ExecutionLog)
            .where(ExecutionLog.execution_id == execution_id)
            .order_by(ExecutionLog.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_timeline(
        self, execution_id: uuid.UUID, owner_api_key_id: uuid.UUID
    ) -> list[ExecutionLog]:
        """Chronological log stream for an execution. Unpaginated for MVP timeline use."""
        await self._check_ownership(execution_id, owner_api_key_id)

        stmt = (
            select(ExecutionLog)
            .where(ExecutionLog.execution_id == execution_id)
            .order_by(ExecutionLog.created_at.asc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())


async def get_execution_log_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ExecutionLogService:
    return ExecutionLogService(db)
