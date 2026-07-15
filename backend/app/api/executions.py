import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.errors import AppError
from app.core.security import require_api_key_id
from app.schemas.execution import (
    CreateExecutionRequest,
    ExecutionLogResponse,
    ExecutionResponse,
    NodeExecutionResponse,
)
from app.services.execution_log_service import ExecutionLogService, get_execution_log_service
from app.transport.contracts import ExecutionEngineClient, StartExecutionCommand
from app.transport.factory import get_execution_engine_client

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


@router.get("", response_model=list[ExecutionResponse])
async def list_executions(
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    client: Annotated[ExecutionEngineClient, Depends(get_execution_engine_client)],
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ExecutionResponse]:
    executions = await client.list_executions(
        owner_api_key_id=owner_id, status=status, limit=limit, offset=offset
    )
    return [ExecutionResponse.model_validate(e) for e in executions]


@router.post("", response_model=ExecutionResponse, status_code=201)
async def create_execution(
    request: CreateExecutionRequest,
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    client: Annotated[ExecutionEngineClient, Depends(get_execution_engine_client)],
) -> ExecutionResponse:
    command = StartExecutionCommand(
        workflow_version_id=request.workflow_version_id,
        input_payload=request.input_payload,
    )
    execution = await client.start_execution(command, owner_id)
    return ExecutionResponse.model_validate(execution)


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    client: Annotated[ExecutionEngineClient, Depends(get_execution_engine_client)],
) -> ExecutionResponse:
    execution = await client.get_execution(execution_id, owner_id)
    if not execution:
        raise AppError("Execution not found", code="not_found", status_code=404)
    return ExecutionResponse.model_validate(execution)


@router.get("/{execution_id}/nodes", response_model=list[NodeExecutionResponse])
async def get_execution_nodes(
    execution_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    client: Annotated[ExecutionEngineClient, Depends(get_execution_engine_client)],
) -> list[NodeExecutionResponse]:
    nodes = await client.get_node_executions(execution_id, owner_id)
    return [NodeExecutionResponse.model_validate(n) for n in nodes]


@router.get("/{execution_id}/logs", response_model=list[ExecutionLogResponse])
async def get_execution_logs(
    execution_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    service: Annotated[ExecutionLogService, Depends(get_execution_log_service)],
    limit: int = 50,
    offset: int = 0,
) -> list[ExecutionLogResponse]:
    logs = await service.list_logs(execution_id, owner_id, limit=limit, offset=offset)
    return [ExecutionLogResponse.from_log(log) for log in logs]


@router.get("/{execution_id}/timeline", response_model=list[ExecutionLogResponse])
async def get_execution_timeline(
    execution_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    service: Annotated[ExecutionLogService, Depends(get_execution_log_service)],
) -> list[ExecutionLogResponse]:
    logs = await service.get_timeline(execution_id, owner_id)
    return [ExecutionLogResponse.from_log(log) for log in logs]
