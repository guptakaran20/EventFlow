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

async def _worker_background_loop():
    import socket, uuid, os
    from app.core.config import get_settings
    from app.db.session import get_session_factory
    from app.models.enums import WorkerStatus
    from app.queue.publisher import InMemoryQueuePublisher, RedisStreamQueuePublisher
    from app.queue.redis_client import get_redis
    from app.services.executor_registry import get_executor_registry
    from app.services.worker_service import WorkerService
    from app.worker.heartbeat import HeartbeatController, run_heartbeat_loop
    from app.worker.recovery import run_recovery_loop
    from app.worker.runtime import run_worker

    settings = get_settings()
    
    def _build_queue_publisher():
        if settings.queue_publisher_backend == "redis":
            return RedisStreamQueuePublisher(
                redis=get_redis(),
                stream_name=settings.redis_stream_name,
                consumer_group=settings.redis_consumer_group,
            )
        return InMemoryQueuePublisher()

    hostname = socket.gethostname()
    consumer_name = settings.worker_name or f"worker-{hostname}-{os.getpid()}-{uuid.uuid4()}"
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        worker = await WorkerService(session).register_worker(consumer_name, hostname)

    stop_event = asyncio.Event()
    heartbeat = HeartbeatController(worker.id)
    await heartbeat.set_status(WorkerStatus.IDLE)

    heartbeat_task = asyncio.create_task(
        run_heartbeat_loop(
            session_factory,
            heartbeat,
            settings.worker_heartbeat_interval_seconds,
            stop_event,
        )
    )
    recovery_task = asyncio.create_task(
        run_recovery_loop(
            session_factory,
            get_executor_registry(),
            _build_queue_publisher(),
            get_redis(),
            settings.redis_stream_name,
            settings.redis_consumer_group,
            consumer_name,
            settings.worker_pending_idle_timeout_seconds,
            settings.worker_recovery_poll_interval_seconds,
            stop_event,
        )
    )
    
    try:
        await run_worker(
            session_factory=session_factory,
            registry=get_executor_registry(),
            queue_publisher=_build_queue_publisher(),
            redis=get_redis(),
            stream_name=settings.redis_stream_name,
            consumer_group=settings.redis_consumer_group,
            consumer_name=consumer_name,
            poll_count=settings.worker_concurrency,
            stop_event=stop_event,
            heartbeat=heartbeat,
        )
    except asyncio.CancelledError:
        pass
    finally:
        await heartbeat.set_status(WorkerStatus.STOPPING)
        stop_event.set()
        await heartbeat_task
        await recovery_task
        async with session_factory() as session:
            await WorkerService(session).mark_offline(worker.id)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_redis_pubsub_listener())
    worker_task = asyncio.create_task(_worker_background_loop())
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
