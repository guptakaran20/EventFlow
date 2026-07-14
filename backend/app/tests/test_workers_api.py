import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import WorkerStatus
from app.services.worker_service import WorkerService


@pytest.fixture
async def db(engine) -> AsyncSession:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.mark.asyncio
async def test_list_workers_api(client, db: AsyncSession):
    service = WorkerService(db)
    await service.register_worker("api-worker-1", "host-a")
    await service.register_worker("api-worker-2", "host-b")

    keys = get_settings().bootstrap_api_keys_list
    if not keys:
        pytest.skip("bootstrap API key required")
    headers = {"X-EventFlow-API-Key": keys[0]}

    response = await client.get("/api/v1/workers", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 2
    assert "worker_id" in body[0]
    assert "hostname" in body[0]
    assert "status" in body[0]


@pytest.mark.asyncio
async def test_get_worker_api(client, db: AsyncSession):
    service = WorkerService(db)
    worker = await service.register_worker("api-worker-single", "host-single")

    keys = get_settings().bootstrap_api_keys_list
    if not keys:
        pytest.skip("bootstrap API key required")
    headers = {"X-EventFlow-API-Key": keys[0]}

    response = await client.get(f"/api/v1/workers/{worker.id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["worker_id"] == str(worker.id)
    assert body["hostname"] == "host-single"
    assert body["status"] == WorkerStatus.STARTING
