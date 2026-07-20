import asyncio
import os
os.environ['DATABASE_URL']='postgresql+asyncpg://eventflow:eventflow@localhost:15432/eventflow_test'
from app.core.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.base import Base
import app.models

async def run():
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(run())
