import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

# Inject required environment variables for tests before any app code is imported
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://eventflow:eventflow@localhost:15432/eventflow_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("JWT_ACCESS_SECRET_KEY", "test-secret-access")
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "test-secret-refresh")
os.environ.setdefault("EVENTFLOW_INTERNAL_TRANSPORT", "local")

import app.models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base
from app.main import app as fastapi_app


@pytest.fixture
async def client():
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session", autouse=True)
async def engine():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(engine):
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
async def api_key(db_session):
    from app.services.api_key_service import APIKeyService

    service = APIKeyService(db_session)
    api_key_obj, raw_key = await service.create("Test Vendor Key")
    return raw_key


@pytest.fixture
async def auth_headers(client, api_key):
    response = await client.post("/api/v1/auth/token", json={"api_key": api_key})
    assert response.status_code == 200, f"Token generation failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
