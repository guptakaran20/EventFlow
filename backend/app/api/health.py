from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.db.session import check_database_connection
from app.queue.redis_client import check_redis_connection

router = APIRouter(prefix="/health", tags=["health"])


class LiveResponse(BaseModel):
    status: str = "ok"


class ReadyResponse(BaseModel):
    status: str
    database: bool
    redis: bool


@router.get("/live", response_model=LiveResponse)
async def live() -> LiveResponse:
    return LiveResponse()


@router.get("/ready", response_model=ReadyResponse)
async def ready(response: Response) -> ReadyResponse:
    database_ok = await check_database_connection()
    redis_ok = await check_redis_connection()
    is_ready = database_ok and redis_ok
    response.status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(
        status="ok" if is_ready else "degraded",
        database=database_ok,
        redis=redis_ok,
    )
