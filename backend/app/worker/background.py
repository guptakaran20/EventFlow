import asyncio
import os
import socket
import uuid

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_session_factory
from app.models.enums import WorkerStatus
from app.queue.publisher import InMemoryQueuePublisher, RedisStreamQueuePublisher
from app.queue.redis_client import get_redis
from app.services.executor_registry import get_executor_registry
from app.services.worker_service import WorkerService
from app.worker.heartbeat import HeartbeatController, run_heartbeat_loop
from app.worker.recovery import run_recovery_loop
from app.worker.runtime import run_worker

_active_background_tasks: set[asyncio.Task] = set()
MAX_SPAWNED_WORKERS = 5


def get_active_worker_count() -> int:
    return len([t for t in _active_background_tasks if not t.done()])


def spawn_background_worker_task(owner_api_key_id: uuid.UUID | None = None) -> asyncio.Task:
    if get_active_worker_count() >= MAX_SPAWNED_WORKERS:
        raise AppError(
            f"Maximum background worker limit reached (max {MAX_SPAWNED_WORKERS})",
            code="worker_limit_reached",
            status_code=429,
        )
    task = asyncio.create_task(start_background_worker(owner_api_key_id))
    _active_background_tasks.add(task)
    task.add_done_callback(_active_background_tasks.discard)
    return task


async def start_background_worker(owner_api_key_id: uuid.UUID | None = None):
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
        worker = await WorkerService(session).register_worker(
            consumer_name, hostname, owner_api_key_id
        )

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
