import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.dlq import DeadLetterJob
from app.models.enums import ExecutionStatus, NodeExecutionStatus, WorkerStatus
from app.models.execution import Execution, NodeExecution
from app.models.worker import Worker
from app.models.workflow import Workflow
from app.queue.publisher import QueuePublisher
from app.schemas.metrics import MetricsSummaryResponse
from app.transport.local_execution_client import get_queue_publisher

ACTIVE_WORKER_STATUSES = (WorkerStatus.IDLE, WorkerStatus.BUSY, WorkerStatus.STARTING)


class MetricsService:
    """Approximate dashboard aggregates via a handful of COUNT queries.

    Execution/node/DLQ counts are scoped to the caller's workflows; workers
    and queue depth are shared infra and reported globally, matching the
    existing (unscoped) workers list endpoint.
    """

    def __init__(self, db: AsyncSession, queue_publisher: QueuePublisher):
        self._db = db
        self._queue_publisher = queue_publisher

    async def get_summary(self, owner_api_key_id: uuid.UUID) -> MetricsSummaryResponse:
        active_executions_stmt = (
            select(func.count())
            .select_from(Execution)
            .join(Workflow, Workflow.id == Execution.workflow_id)
            .where(
                Workflow.owner_api_key_id == owner_api_key_id,
                Execution.status == ExecutionStatus.RUNNING,
            )
        )
        node_status_stmt = (
            select(NodeExecution.status, func.count())
            .select_from(NodeExecution)
            .join(Execution, Execution.id == NodeExecution.execution_id)
            .join(Workflow, Workflow.id == Execution.workflow_id)
            .where(
                Workflow.owner_api_key_id == owner_api_key_id,
                NodeExecution.status.in_([NodeExecutionStatus.QUEUED, NodeExecutionStatus.RUNNING]),
            )
            .group_by(NodeExecution.status)
        )
        dlq_stmt = (
            select(func.count())
            .select_from(DeadLetterJob)
            .join(Execution, Execution.id == DeadLetterJob.execution_id)
            .join(Workflow, Workflow.id == Execution.workflow_id)
            .where(
                Workflow.owner_api_key_id == owner_api_key_id,
                DeadLetterJob.resolved_at.is_(None),
            )
        )
        workers_stmt = select(Worker.status, func.count()).group_by(Worker.status)

        active_executions = (await self._db.execute(active_executions_stmt)).scalar_one()
        node_status_counts = dict((await self._db.execute(node_status_stmt)).all())
        dead_letter_jobs = (await self._db.execute(dlq_stmt)).scalar_one()
        worker_status_counts = dict((await self._db.execute(workers_stmt)).all())

        queue_depth = await self._get_queue_depth()

        workers = sum(worker_status_counts.values())
        active_workers = sum(
            count
            for status, count in worker_status_counts.items()
            if status in ACTIVE_WORKER_STATUSES
        )

        return MetricsSummaryResponse(
            active_executions=active_executions,
            queued_nodes=node_status_counts.get(NodeExecutionStatus.QUEUED, 0),
            running_nodes=node_status_counts.get(NodeExecutionStatus.RUNNING, 0),
            workers=workers,
            active_workers=active_workers,
            queue_depth=queue_depth,
            dead_letter_jobs=dead_letter_jobs,
        )

    async def _get_queue_depth(self) -> int:
        queue_depth_fn = getattr(self._queue_publisher, "queue_depth", None)
        if queue_depth_fn is None:
            return 0
        return await queue_depth_fn()


async def get_metrics_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    queue_publisher: Annotated[QueuePublisher, Depends(get_queue_publisher)],
) -> MetricsService:
    return MetricsService(db, queue_publisher)
