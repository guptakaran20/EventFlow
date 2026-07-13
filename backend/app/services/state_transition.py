import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.enums import ExecutionStatus, NodeExecutionStatus
from app.models.execution import Execution, NodeExecution


class StateTransitionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def transition_execution_status(
        self,
        execution_id: uuid.UUID,
        from_status: ExecutionStatus,
        to_status: ExecutionStatus,
    ) -> Execution:
        """Transitions execution status with validation."""
        stmt = select(Execution).where(Execution.id == execution_id)
        result = await self.session.execute(stmt)
        execution = result.scalar_one_or_none()

        if not execution:
            raise AppError("Execution not found", code="not_found", status_code=404)

        if execution.status != from_status:
            raise AppError(
                f"Invalid execution transition: cannot transition from {execution.status.name} "
                f"to {to_status.name} (expected {from_status.name})",
                code="invalid_transition",
            )

        execution.status = to_status

        if to_status == ExecutionStatus.RUNNING:
            execution.started_at = datetime.now(UTC)
        elif to_status in (
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
            ExecutionStatus.PARTIAL_FAILED,
            ExecutionStatus.CANCELLED,
        ):
            execution.finished_at = datetime.now(UTC)

        await self.session.flush()
        return execution

    async def transition_node_status(
        self,
        node_execution_id: uuid.UUID,
        from_status: NodeExecutionStatus,
        to_status: NodeExecutionStatus,
        metadata: dict[str, Any] | None = None,
    ) -> NodeExecution:
        """Transitions node status with validation."""
        stmt = select(NodeExecution).where(NodeExecution.id == node_execution_id)
        result = await self.session.execute(stmt)
        node = result.scalar_one_or_none()

        if not node:
            raise AppError("NodeExecution not found", code="not_found", status_code=404)

        if node.status != from_status:
            raise AppError(
                f"Invalid node transition: cannot transition from {node.status.name} "
                f"to {to_status.name} (expected {from_status.name})",
                code="invalid_transition",
            )

        node.status = to_status

        if to_status == NodeExecutionStatus.QUEUED:
            node.queued_at = datetime.now(UTC)
            # FAILED -> RETRYING -> QUEUED means it increments attempt.
            # Or if it's the first time QUEUED from PENDING, set attempt to 1 if it's 0.
            if node.attempt == 0:
                node.attempt = 1
        elif to_status == NodeExecutionStatus.RUNNING:
            node.started_at = datetime.now(UTC)
        elif to_status in (
            NodeExecutionStatus.SUCCEEDED,
            NodeExecutionStatus.FAILED,
            NodeExecutionStatus.SKIPPED,
            NodeExecutionStatus.DEAD_LETTERED,
        ):
            node.finished_at = datetime.now(UTC)

        await self.session.flush()
        return node
