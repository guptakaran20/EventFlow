from typing import Annotated

from fastapi import Depends

from app.core.config import TransportMode, get_settings
from app.transport.contracts import ExecutionEngineClient
from app.transport.local_execution_client import (
    LocalExecutionEngineClient,
    get_local_execution_client,
)


async def get_execution_engine_client(
    local_client: Annotated["LocalExecutionEngineClient", Depends(get_local_execution_client)],
) -> ExecutionEngineClient:
    """Dependency injection factory for the execution client."""
    settings = get_settings()

    if settings.eventflow_internal_transport == TransportMode.GRPC:
        from app.transport.grpc_execution_client import GrpcExecutionEngineClient

        return GrpcExecutionEngineClient()

    return local_client
