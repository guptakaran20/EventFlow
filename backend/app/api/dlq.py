import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.errors import AppError
from app.core.security import require_api_key_id
from app.schemas.dlq import DeadLetterJobResponse, ResolveDlqRequest
from app.services.dlq_service import DlqService, get_dlq_service

router = APIRouter(prefix="/api/v1/dlq", tags=["dlq"])


@router.get("", response_model=list[DeadLetterJobResponse])
async def list_dlq_jobs(
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    service: Annotated[DlqService, Depends(get_dlq_service)],
    limit: Annotated[int, Query(ge=0, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DeadLetterJobResponse]:
    jobs = await service.list_dlq_jobs(owner_id, limit=limit, offset=offset)
    return [DeadLetterJobResponse.model_validate(job) for job in jobs]


@router.get("/{dlq_id}", response_model=DeadLetterJobResponse)
async def get_dlq_job(
    dlq_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    service: Annotated[DlqService, Depends(get_dlq_service)],
) -> DeadLetterJobResponse:
    job = await service.get_dlq_job(dlq_id, owner_id)
    if job is None:
        raise AppError("Dead letter job not found", code="not_found", status_code=404)
    return DeadLetterJobResponse.model_validate(job)


@router.post("/{dlq_id}/resolve", response_model=DeadLetterJobResponse)
async def resolve_dlq_job(
    dlq_id: uuid.UUID,
    request: ResolveDlqRequest,
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    service: Annotated[DlqService, Depends(get_dlq_service)],
) -> DeadLetterJobResponse:
    job = await service.resolve_dlq_job(dlq_id, owner_id, request.resolution_note)
    return DeadLetterJobResponse.model_validate(job)
