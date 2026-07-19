import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import AuthenticatedPrincipal, require_api_key, require_api_key_id
from app.schemas.workflow import (
    CreateWorkflowRequest,
    CreateWorkflowVersionRequest,
    WorkflowDefinition,
    WorkflowDetailResponse,
    WorkflowListResponse,
    WorkflowVersionResponse,
)
from app.services.dag_validator import ValidationResult, validate_workflow
from app.services.executor_registry import ExecutorRegistry, get_executor_registry
from app.services.workflow_service import WorkflowService, get_workflow_service

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


@router.post("/validate", response_model=ValidationResult)
async def validate_workflow_endpoint(
    workflow: WorkflowDefinition,
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_api_key)],
    registry: Annotated[ExecutorRegistry, Depends(get_executor_registry)],
) -> ValidationResult:
    """Validate a workflow definition for DAG correctness and executor config."""
    return validate_workflow(workflow, registry)


@router.post("", response_model=WorkflowVersionResponse, status_code=201)
async def create_workflow(
    request: CreateWorkflowRequest,
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> WorkflowVersionResponse:
    workflow, version = await service.create_workflow(
        name=request.name,
        description=request.description,
        definition=request.definition,
        owner_api_key_id=owner_id,
    )
    return WorkflowVersionResponse(
        id=version.id,
        workflow_id=version.workflow_id,
        version_number=version.version_number,
        checksum=version.checksum,
        created_at=version.created_at,
        definition=version.definition,
    )


@router.get("", response_model=list[WorkflowListResponse])
async def list_workflows(
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
    limit: int = 50,
    offset: int = 0,
) -> list[WorkflowListResponse]:
    rows = await service.list_workflows(owner_id, limit=limit, offset=offset)
    return [
        WorkflowListResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            latest_version_number=latest_v,
        )
        for workflow, latest_v in rows
    ]


@router.get("/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow(
    workflow_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> WorkflowDetailResponse:
    workflow = await service.get_workflow(workflow_id, owner_id)
    if not workflow:
        from app.core.errors import AppError

        raise AppError("Workflow not found", code="not_found", status_code=404)

    versions = [
        WorkflowVersionResponse(
            id=v.id,
            workflow_id=v.workflow_id,
            version_number=v.version_number,
            checksum=v.checksum,
            created_at=v.created_at,
            definition=v.definition,
        )
        for v in workflow.versions
    ]
    # Sort versions descending by number
    versions.sort(key=lambda x: x.version_number, reverse=True)

    return WorkflowDetailResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        versions=versions,
    )


@router.post("/{workflow_id}/versions", response_model=WorkflowVersionResponse, status_code=201)
async def create_workflow_version(
    workflow_id: uuid.UUID,
    request: CreateWorkflowVersionRequest,
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> WorkflowVersionResponse:
    version = await service.create_workflow_version(
        workflow_id=workflow_id,
        definition=request.definition,
        owner_api_key_id=owner_id,
    )
    return WorkflowVersionResponse(
        id=version.id,
        workflow_id=version.workflow_id,
        version_number=version.version_number,
        checksum=version.checksum,
        created_at=version.created_at,
        definition=version.definition,
    )


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> None:
    deleted = await service.delete_workflow(workflow_id, owner_id)
    if not deleted:
        from app.core.errors import AppError
        raise AppError("Workflow not found", code="not_found", status_code=404)

