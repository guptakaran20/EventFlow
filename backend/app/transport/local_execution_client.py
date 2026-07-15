from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.queue.publisher import InMemoryQueuePublisher, QueuePublisher, RedisStreamQueuePublisher
from app.queue.redis_client import get_redis
from app.services.execution_engine import ExecutionEngine
from app.services.executor_registry import ExecutorRegistry, get_executor_registry
from app.transport.contracts import (
    ExecutionDTO,
    NodeExecutionDTO,
    StartExecutionCommand,
    TransitionNodeCommand,
)


async def get_queue_publisher() -> QueuePublisher:
    # Singleton publisher selected via settings.queue_publisher_backend
    # ("memory" default, no Redis required; "redis" for RedisStreamQueuePublisher).
    # Tests override this dependency directly regardless of the default.
    if not hasattr(get_queue_publisher, "_instance"):
        settings = get_settings()
        if settings.queue_publisher_backend == "redis":
            get_queue_publisher._instance = RedisStreamQueuePublisher(
                redis=get_redis(),
                stream_name=settings.redis_stream_name,
                consumer_group=settings.redis_consumer_group,
            )
        else:
            get_queue_publisher._instance = InMemoryQueuePublisher()
    return get_queue_publisher._instance


async def get_local_execution_client(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    registry: Annotated[ExecutorRegistry, Depends(get_executor_registry)],
    queue_publisher: Annotated[QueuePublisher, Depends(get_queue_publisher)],
) -> "LocalExecutionEngineClient":
    return LocalExecutionEngineClient(ExecutionEngine(session, registry, queue_publisher))


class LocalExecutionEngineClient:
    """Direct in-process implementation of `ExecutionEngineClient`."""

    def __init__(self, engine: ExecutionEngine):
        self.engine = engine

    async def start_execution(
        self, command: StartExecutionCommand, owner_api_key_id: UUID
    ) -> ExecutionDTO:
        return await self.engine.start_execution(command, owner_api_key_id)

    async def get_execution(
        self, execution_id: UUID, owner_api_key_id: UUID
    ) -> ExecutionDTO | None:
        return await self.engine.get_execution(execution_id, owner_api_key_id)

    async def list_executions(
        self,
        owner_api_key_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ExecutionDTO]:
        return await self.engine.list_executions(owner_api_key_id, status, limit, offset)

    async def get_node_executions(
        self, execution_id: UUID, owner_api_key_id: UUID
    ) -> list[NodeExecutionDTO]:
        return await self.engine.get_node_executions(execution_id, owner_api_key_id)

    async def transition_node(self, command: TransitionNodeCommand) -> NodeExecutionDTO:
        return await self.engine.transition_node(command)

    async def retry_node(
        self, execution_id: UUID, node_id: str, owner_api_key_id: UUID
    ) -> NodeExecutionDTO:
        return await self.engine.retry_node(execution_id, node_id, owner_api_key_id)
