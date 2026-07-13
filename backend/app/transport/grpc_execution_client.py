from uuid import UUID

from app.transport.contracts import (
    ExecutionDTO,
    NodeExecutionDTO,
    StartExecutionCommand,
    TransitionNodeCommand,
)


class GrpcExecutionEngineClient:
    """gRPC-backed implementation of `ExecutionEngineClient`.

    Calls the generated `ExecutionEngineService` stub (docs/18-grpc-transport.md).
    Proto contracts and generated stubs are added in Phase 5.5; gRPC mode is
    not exercised until the REST/local path is fully working.
    """

    async def start_execution(self, command: StartExecutionCommand) -> ExecutionDTO:
        raise NotImplementedError("gRPC transport is implemented in Phase 5.5")

    async def get_execution(self, execution_id: UUID) -> ExecutionDTO:
        raise NotImplementedError("gRPC transport is implemented in Phase 5.5")

    async def transition_node(self, command: TransitionNodeCommand) -> NodeExecutionDTO:
        raise NotImplementedError("gRPC transport is implemented in Phase 5.5")
