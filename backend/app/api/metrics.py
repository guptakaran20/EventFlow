import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import require_api_key_id
from app.schemas.metrics import MetricsSummaryResponse
from app.services.metrics_service import MetricsService, get_metrics_service

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    owner_id: Annotated[uuid.UUID, Depends(require_api_key_id)],
    service: Annotated[MetricsService, Depends(get_metrics_service)],
) -> MetricsSummaryResponse:
    return await service.get_summary(owner_id)
