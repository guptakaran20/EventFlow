"""Application-facing contracts for the internal execution engine transport.

Routers and workers depend on `ExecutionEngineClient`, never on a concrete
`LocalExecutionEngineClient` or `GrpcExecutionEngineClient`. This keeps
business logic independent of whether the engine is reached in-process or
over gRPC (see docs/18-grpc-transport.md).

The engine itself (state machine, DAG execution) is built in Phase 4/5; this
module only defines the shape of the boundary so the transport switch can be
wired up before that logic exists.
"""

from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel


class StartExecutionCommand(BaseModel):
    workflow_version_id: UUID
    input_payload: dict[str, Any] = {}


class TransitionNodeCommand(BaseModel):
    execution_id: UUID
    node_execution_id: UUID
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None


class NodeExecutionDTO(BaseModel):
    id: UUID
    execution_id: UUID
    node_id: str
    node_type: str
    status: str
    attempt: int
    max_attempts: int
    input_payload: dict[str, Any] | None = None
    output_payload: dict[str, Any] | None = None
    error_message: str | None = None


class ExecutionDTO(BaseModel):
    id: UUID
    workflow_id: UUID
    workflow_version_id: UUID
    status: str
    input_payload: dict[str, Any] | None = None
    error_message: str | None = None
    node_executions: list[NodeExecutionDTO] = []


class ExecutionEngineClient(Protocol):
    """Engine capabilities the API and worker call, regardless of transport."""

    async def start_execution(
        self, command: StartExecutionCommand, owner_api_key_id: UUID
    ) -> ExecutionDTO: ...

    async def get_execution(
        self, execution_id: UUID, owner_api_key_id: UUID
    ) -> ExecutionDTO | None: ...

    async def list_executions(
        self,
        owner_api_key_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ExecutionDTO]: ...

    async def get_node_executions(
        self, execution_id: UUID, owner_api_key_id: UUID
    ) -> list[NodeExecutionDTO]: ...

    async def transition_node(self, command: TransitionNodeCommand) -> NodeExecutionDTO: ...

    async def retry_node(
        self, execution_id: UUID, node_id: str, owner_api_key_id: UUID
    ) -> NodeExecutionDTO: ...
