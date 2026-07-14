from uuid import UUID

import grpc
from google.protobuf.struct_pb2 import Struct

from app.transport.contracts import (
    ExecutionDTO,
    NodeExecutionDTO,
    StartExecutionCommand,
    TransitionNodeCommand,
)
from app.transport.eventflow import execution_engine_pb2 as pb
from app.transport.eventflow import execution_engine_pb2_grpc as pb_grpc


class GrpcExecutionEngineClient:
    """gRPC-backed implementation of `ExecutionEngineClient`.

    Calls the generated `ExecutionEngineService` stub (docs/18-grpc-transport.md).
    Proto contracts and generated stubs are added in Phase 5.5; gRPC mode is
    not exercised until the REST/local path is fully working.
    """

    def __init__(self, target: str = "localhost:50051"):
        self.target = target

    async def _get_stub(self):
        channel = grpc.aio.insecure_channel(self.target)
        return pb_grpc.ExecutionEngineServiceStub(channel)

    async def start_execution(
        self, command: StartExecutionCommand, owner_api_key_id: UUID
    ) -> ExecutionDTO:
        stub = await self._get_stub()
        req = pb.StartExecutionRequest(
            workflow_version_id=str(command.workflow_version_id),
            owner_api_key_id=str(owner_api_key_id),
        )
        if command.input_payload:
            s = Struct()
            s.update(command.input_payload)
            req.input_payload.CopyFrom(s)

        resp = await stub.StartExecution(req)
        return self._map_execution(resp)

    async def get_execution(
        self, execution_id: UUID, owner_api_key_id: UUID
    ) -> ExecutionDTO | None:
        stub = await self._get_stub()
        req = pb.GetExecutionRequest(
            execution_id=str(execution_id), owner_api_key_id=str(owner_api_key_id)
        )
        try:
            resp = await stub.GetExecution(req)
            return self._map_execution(resp)
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return None
            raise

    async def get_node_executions(
        self, execution_id: UUID, owner_api_key_id: UUID
    ) -> list[NodeExecutionDTO]:
        stub = await self._get_stub()
        req = pb.GetNodeExecutionsRequest(
            execution_id=str(execution_id), owner_api_key_id=str(owner_api_key_id)
        )
        resp = await stub.GetNodeExecutions(req)
        return [self._map_node_execution(n) for n in resp.node_executions]

    async def transition_node(self, command: TransitionNodeCommand) -> NodeExecutionDTO:
        stub = await self._get_stub()
        req = pb.TransitionNodeRequest(
            execution_id=str(command.execution_id),
            node_execution_id=str(command.node_execution_id),
            status=command.status,
        )
        if command.result:
            s = Struct()
            s.update(command.result)
            req.result.CopyFrom(s)
        if command.error:
            req.error = command.error

        resp = await stub.TransitionNode(req)
        return self._map_node_execution(resp)

    def _map_execution(self, msg: pb.ExecutionDTO) -> ExecutionDTO:
        return ExecutionDTO(
            id=UUID(msg.id),
            workflow_id=UUID(msg.workflow_id),
            workflow_version_id=UUID(msg.workflow_version_id),
            status=msg.status,
            input_payload=dict(msg.input_payload.items()) if msg.input_payload else None,
            error_message=msg.error_message if msg.HasField("error_message") else None,
            node_executions=[self._map_node_execution(n) for n in msg.node_executions],
        )

    def _map_node_execution(self, msg: pb.NodeExecutionDTO) -> NodeExecutionDTO:
        return NodeExecutionDTO(
            id=UUID(msg.id),
            execution_id=UUID(msg.execution_id),
            node_id=msg.node_id,
            node_type=msg.node_type,
            status=msg.status,
            attempt=msg.attempt,
            max_attempts=msg.max_attempts,
            input_payload=dict(msg.input_payload.items()) if msg.input_payload else None,
            output_payload=dict(msg.output_payload.items()) if msg.output_payload else None,
            error_message=msg.error_message if msg.HasField("error_message") else None,
        )
