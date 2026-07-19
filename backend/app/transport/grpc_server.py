import asyncio
import logging
from uuid import UUID

import grpc
from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import Struct

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.queue.publisher import InMemoryQueuePublisher, RedisStreamQueuePublisher
from app.queue.redis_client import get_redis
from app.services.execution_engine import ExecutionEngine
from app.services.executor_registry import get_executor_registry
from app.transport.contracts import StartExecutionCommand, TransitionNodeCommand
from app.transport.eventflow import execution_engine_pb2 as pb
from app.transport.eventflow import execution_engine_pb2_grpc as pb_grpc

logger = logging.getLogger(__name__)


class ExecutionEngineServiceServicer(pb_grpc.ExecutionEngineServiceServicer):
    def __init__(self, registry, queue_publisher):
        self.registry = registry
        self.queue_publisher = queue_publisher

    def _map_execution_dto_to_pb(self, dto) -> pb.ExecutionDTO:
        msg = pb.ExecutionDTO(
            id=str(dto.id),
            workflow_id=str(dto.workflow_id),
            workflow_version_id=str(dto.workflow_version_id),
            status=dto.status,
        )
        if dto.input_payload:
            s = Struct()
            s.update(dto.input_payload)
            msg.input_payload.CopyFrom(s)
        if dto.error_message:
            msg.error_message = dto.error_message

        for node_dto in dto.node_executions:
            msg.node_executions.append(self._map_node_execution_dto_to_pb(node_dto))
            
        return msg

    def _map_node_execution_dto_to_pb(self, dto) -> pb.NodeExecutionDTO:
        msg = pb.NodeExecutionDTO(
            id=str(dto.id),
            execution_id=str(dto.execution_id),
            node_id=dto.node_id,
            node_type=dto.node_type,
            status=dto.status,
            attempt=dto.attempt,
            max_attempts=dto.max_attempts,
        )
        if dto.input_payload:
            s = Struct()
            s.update(dto.input_payload)
            msg.input_payload.CopyFrom(s)
        if dto.output_payload:
            s = Struct()
            s.update(dto.output_payload)
            msg.output_payload.CopyFrom(s)
        if dto.error_message:
            msg.error_message = dto.error_message
        return msg

    async def StartExecution(self, request, context):
        try:
            command = StartExecutionCommand(
                workflow_version_id=UUID(request.workflow_version_id),
                input_payload=dict(request.input_payload.items()) if request.input_payload else {},
            )
            owner_id = UUID(request.owner_api_key_id)
            session_factory = get_session_factory()
            async with session_factory() as session:
                engine = ExecutionEngine(session, self.registry, self.queue_publisher)
                dto = await engine.start_execution(command, owner_id)
                return self._map_execution_dto_to_pb(dto)
        except Exception as e:
            logger.exception("Error in StartExecution")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    async def GetExecution(self, request, context):
        try:
            execution_id = UUID(request.execution_id)
            owner_id = UUID(request.owner_api_key_id)
            session_factory = get_session_factory()
            async with session_factory() as session:
                engine = ExecutionEngine(session, self.registry, self.queue_publisher)
                dto = await engine.get_execution(execution_id, owner_id)
                if not dto:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details("Execution not found")
                    return pb.ExecutionDTO()
                return self._map_execution_dto_to_pb(dto)
        except Exception as e:
            logger.exception("Error in GetExecution")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    async def ListExecutions(self, request, context):
        try:
            owner_id = UUID(request.owner_api_key_id)
            status = request.status if request.HasField("status") else None
            limit = request.limit if request.limit else 50
            offset = request.offset if request.offset else 0
            
            session_factory = get_session_factory()
            async with session_factory() as session:
                engine = ExecutionEngine(session, self.registry, self.queue_publisher)
                dtos = await engine.list_executions(owner_id, status=status, limit=limit, offset=offset)
                
                resp = pb.ExecutionListDTO()
                for dto in dtos:
                    resp.executions.append(self._map_execution_dto_to_pb(dto))
                return resp
        except Exception as e:
            logger.exception("Error in ListExecutions")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    async def GetNodeExecutions(self, request, context):
        try:
            execution_id = UUID(request.execution_id)
            owner_id = UUID(request.owner_api_key_id)
            session_factory = get_session_factory()
            async with session_factory() as session:
                engine = ExecutionEngine(session, self.registry, self.queue_publisher)
                dtos = await engine.get_node_executions(execution_id, owner_id)
                
                resp = pb.NodeExecutionListDTO()
                for dto in dtos:
                    resp.node_executions.append(self._map_node_execution_dto_to_pb(dto))
                return resp
        except Exception as e:
            logger.exception("Error in GetNodeExecutions")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    async def TransitionNode(self, request, context):
        try:
            execution_id = UUID(request.execution_id)
            node_execution_id = UUID(request.node_execution_id)
            status = request.status
            result = MessageToDict(request.result) if request.HasField("result") else None
            error = request.error if request.HasField("error") else None

            session_factory = get_session_factory()
            async with session_factory() as session:
                engine = ExecutionEngine(session, self.registry, self.queue_publisher)
                command = TransitionNodeCommand(
                    execution_id=execution_id,
                    node_execution_id=node_execution_id,
                    status=status,
                    result=result,
                    error=error,
                )
                dto = await engine.transition_node(command)
                return self._map_node_execution_dto_to_pb(dto)
        except Exception as e:
            logger.exception("Error in TransitionNode")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    async def RetryNode(self, request, context):
        try:
            execution_id = UUID(request.execution_id)
            node_id = request.node_id
            owner_id = UUID(request.owner_api_key_id)

            session_factory = get_session_factory()
            async with session_factory() as session:
                engine = ExecutionEngine(session, self.registry, self.queue_publisher)
                dto = await engine.retry_node(execution_id, node_id, owner_id)
                return self._map_node_execution_dto_to_pb(dto)
        except Exception as e:
            logger.exception("Error in RetryNode")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    async def DeleteExecution(self, request, context):
        try:
            execution_id = UUID(request.execution_id)
            owner_id = UUID(request.owner_api_key_id)

            session_factory = get_session_factory()
            async with session_factory() as session:
                engine = ExecutionEngine(session, self.registry, self.queue_publisher)
                await engine.delete_execution(execution_id, owner_id)
                return pb.DeleteExecutionResponse()
        except Exception as e:
            logger.exception("Error in DeleteExecution")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise


class GrpcServerContext:
    def __init__(self):
        self.server = None

    async def start(self, port=50051):
        settings = get_settings()
        
        # Initialize dependencies
        if settings.queue_publisher_backend == "redis":
            redis_client = get_redis()
            publisher = RedisStreamQueuePublisher(
                redis=redis_client,
                stream_name=settings.redis_stream_name,
                consumer_group=settings.redis_consumer_group,
            )
        else:
            publisher = InMemoryQueuePublisher()
            
        registry = get_executor_registry()
        
        self.server = grpc.aio.server()
        servicer = ExecutionEngineServiceServicer(registry, publisher)
        pb_grpc.add_ExecutionEngineServiceServicer_to_server(servicer, self.server)
        
        self.server.add_insecure_port(f"[::]:{port}")
        await self.server.start()
        logger.info(f"gRPC ExecutionEngineService started on port {port}")

    async def stop(self):
        if self.server:
            logger.info("Stopping gRPC ExecutionEngineService...")
            await self.server.stop(grace=5)

_grpc_server_context = GrpcServerContext()

async def start_grpc_server():
    await _grpc_server_context.start()

async def stop_grpc_server():
    await _grpc_server_context.stop()
