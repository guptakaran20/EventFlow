import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=10)
    initial_interval: int = Field(default=1, ge=1)
    max_interval: int = Field(default=3600, ge=1)
    backoff_multiplier: float = Field(default=2.0, ge=1.0)


class Node(BaseModel):
    id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    name: str = Field(default="")
    config: dict[str, Any] = Field(default_factory=dict)
    retry_policy: RetryPolicy | None = None


class Edge(BaseModel):
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    condition: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class WorkflowDefinition(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    nodes: list[Node]
    edges: list[Edge] = Field(default_factory=list)
    default_retry_policy: RetryPolicy | None = None


class WorkflowResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class WorkflowListResponse(WorkflowResponse):
    latest_version_number: int


class WorkflowVersionResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    version_number: int
    checksum: str
    created_at: datetime
    definition: dict[str, Any] | None = None


class WorkflowDetailResponse(WorkflowResponse):
    versions: list[WorkflowVersionResponse]


class CreateWorkflowRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    definition: WorkflowDefinition


class CreateWorkflowVersionRequest(BaseModel):
    definition: WorkflowDefinition
