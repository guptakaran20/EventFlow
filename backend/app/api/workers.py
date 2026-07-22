import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.security import require_api_key_id
from app.schemas.worker import WorkerResponse
from app.services.worker_service import WorkerService, get_worker_service
from app.worker.background import spawn_background_worker_task

router = APIRouter(prefix="/api/v1/workers", tags=["workers"])


@router.get("", response_model=list[WorkerResponse])
async def list_workers(
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    service: Annotated[WorkerService, Depends(get_worker_service)],
    limit: Annotated[int, Query(ge=0, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[WorkerResponse]:
    workers = await service.list_workers(owner_id, limit=limit, offset=offset)
    return [WorkerResponse.from_worker(w) for w in workers]


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(
    worker_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    service: Annotated[WorkerService, Depends(get_worker_service)],
) -> WorkerResponse:
    worker = await service.require_worker(worker_id, owner_id)
    return WorkerResponse.from_worker(worker)


@router.post("/spawn", status_code=202)
async def spawn_worker(
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
):
    spawn_background_worker_task(owner_id)
    return {"message": "Spawned new worker in background"}
