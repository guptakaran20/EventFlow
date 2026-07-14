import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import LogLevel


class CreateExecutionRequest(BaseModel):
    workflow_version_id: uuid.UUID
    input_payload: dict[str, Any] = {}


class NodeExecutionResponse(BaseModel):
    id: uuid.UUID
    execution_id: uuid.UUID
    node_id: str
    node_type: str
    status: str
    attempt: int
    max_attempts: int
    input_payload: dict[str, Any] | None = None
    output_payload: dict[str, Any] | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ExecutionResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    workflow_version_id: uuid.UUID
    status: str
    input_payload: dict[str, Any] | None = None
    error_message: str | None = None
    node_executions: list[NodeExecutionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ExecutionLogResponse(BaseModel):
    log_id: uuid.UUID
    timestamp: datetime
    level: LogLevel
    message: str
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_log(cls, log) -> "ExecutionLogResponse":
        return cls(
            log_id=log.id,
            timestamp=log.created_at,
            level=log.level,
            message=log.message,
            metadata=log.log_metadata,
        )
