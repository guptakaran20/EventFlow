from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.queue.publisher import InMemoryQueuePublisher, QueuePublisher
from app.services.execution_engine import ExecutionEngine
from app.services.executor_registry import ExecutorRegistry, get_executor_registry
from app.transport.contracts import (
    ExecutionDTO,
    NodeExecutionDTO,
    StartExecutionCommand,
    TransitionNodeCommand,
)


async def get_queue_publisher() -> QueuePublisher:
    # MVP: singleton in-memory publisher for local testing.
    # We would normally inject a RedisPublisher here.
    if not hasattr(get_queue_publisher, "_instance"):
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

    async def get_node_executions(
        self, execution_id: UUID, owner_api_key_id: UUID
    ) -> list[NodeExecutionDTO]:
        return await self.engine.get_node_executions(execution_id, owner_api_key_id)

    async def transition_node(self, command: TransitionNodeCommand) -> NodeExecutionDTO:
        return await self.engine.transition_node(command)
