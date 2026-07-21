import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import require_api_key
from app.schemas.worker import WorkerResponse
from app.services.worker_service import WorkerService, get_worker_service
from app.worker.background import spawn_background_worker_task

router = APIRouter(prefix="/api/v1/workers", tags=["workers"])


@router.get("", response_model=list[WorkerResponse])
async def list_workers(
    _: Annotated[object, Depends(require_api_key)],
    service: Annotated[WorkerService, Depends(get_worker_service)],
    limit: int = 50,
    offset: int = 0,
) -> list[WorkerResponse]:
    workers = await service.list_workers(limit=limit, offset=offset)
    return [WorkerResponse.from_worker(w) for w in workers]


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(
    worker_id: uuid.UUID,
    _: Annotated[object, Depends(require_api_key)],
    service: Annotated[WorkerService, Depends(get_worker_service)],
) -> WorkerResponse:
    worker = await service.require_worker(worker_id)
    return WorkerResponse.from_worker(worker)


@router.post("/spawn", status_code=202)
async def spawn_worker(
    _: Annotated[object, Depends(require_api_key)],
):
    spawn_background_worker_task()
    return {"message": "Spawned new worker in background"}
