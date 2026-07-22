import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WorkerStatus
from app.services.worker_service import WorkerService


@pytest.fixture
async def db(engine) -> AsyncSession:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.mark.asyncio
async def test_list_workers_api(client, db: AsyncSession, auth_headers):
    import jwt

    token = auth_headers["Authorization"].split("Bearer ")[1]
    payload = jwt.decode(token, options={"verify_signature": False})
    owner_id = payload["api_key_id"]

    service = WorkerService(db)
    await service.register_worker("api-worker-1", "host-a", owner_id)
    await service.register_worker("api-worker-2", "host-b", owner_id)

    # Test list endpoint

    response = await client.get("/api/v1/workers", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 2
    assert "worker_id" in body[0]
    assert "hostname" in body[0]
    assert "status" in body[0]


@pytest.mark.asyncio
async def test_get_worker_api(client, db: AsyncSession, auth_headers):
    import jwt

    token = auth_headers["Authorization"].split("Bearer ")[1]
    payload = jwt.decode(token, options={"verify_signature": False})
    owner_id = payload["api_key_id"]

    service = WorkerService(db)
    worker = await service.register_worker("api-worker-single", "host-single", owner_id)

    # Test get endpoint

    response = await client.get(f"/api/v1/workers/{worker.id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["worker_id"] == str(worker.id)
    assert body["hostname"] == "host-single"
    assert body["status"] == WorkerStatus.STARTING.value


@pytest.mark.asyncio
async def test_spawn_worker_limit_exceeded(client, auth_headers, monkeypatch):
    from app.worker import background

    monkeypatch.setattr(background, "get_active_worker_count", lambda: 5)

    response = await client.post("/api/v1/workers/spawn", headers=auth_headers)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "worker_limit_reached"
