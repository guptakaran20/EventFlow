from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, health
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.db.session import dispose_engine
from app.queue.redis_client import close_redis


import asyncio
import json
import logging
from app.websocket.connection_manager import get_connection_manager

async def _redis_pubsub_listener():
    from app.queue.redis_client import get_redis
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe("eventflow:ws")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    payload = json.loads(message["data"])
                    await get_connection_manager().broadcast(payload["execution_id"], payload["message"])
                except Exception:
                    logging.getLogger("app.websocket").exception("Failed to process pubsub message")
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe("eventflow:ws")

from app.worker.background import start_background_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_redis_pubsub_listener())
    worker_task = asyncio.create_task(start_background_worker())
    yield
    task.cancel()
    worker_task.cancel()
    try:
        await task
        await worker_task
    except asyncio.CancelledError:
        pass
    await dispose_engine()
    await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Distributed workflow orchestration engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router)

    from app.api import workflows

    app.include_router(workflows.router)

    from app.api import executions

    app.include_router(executions.router)

    from app.api import dlq

    app.include_router(dlq.router)

    from app.api import workers

    app.include_router(workers.router)

    from app.api import metrics

    app.include_router(metrics.router)

    from app.api import websocket

    app.include_router(websocket.router)

    return app


app = create_app()

# Force reload to pick up .env changes
