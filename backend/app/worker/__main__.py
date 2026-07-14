import asyncio
import logging
import os
import socket
import uuid

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.models.enums import WorkerStatus
from app.queue.publisher import InMemoryQueuePublisher, QueuePublisher, RedisStreamQueuePublisher
from app.queue.redis_client import get_redis
from app.services.executor_registry import get_executor_registry
from app.services.worker_service import WorkerService
from app.worker.heartbeat import HeartbeatController, run_heartbeat_loop
from app.worker.recovery import run_recovery_loop
from app.worker.runtime import run_worker

logger = logging.getLogger("app.worker")


def _build_queue_publisher(settings) -> QueuePublisher:
    if settings.queue_publisher_backend == "redis":
        return RedisStreamQueuePublisher(
            redis=get_redis(),
            stream_name=settings.redis_stream_name,
            consumer_group=settings.redis_consumer_group,
        )
    return InMemoryQueuePublisher()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    hostname = socket.gethostname()
    consumer_name = settings.worker_name or f"worker-{hostname}-{os.getpid()}-{uuid.uuid4()}"
    logger.info("starting worker %s", consumer_name)

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
            _build_queue_publisher(settings),
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
            queue_publisher=_build_queue_publisher(settings),
            redis=get_redis(),
            stream_name=settings.redis_stream_name,
            consumer_group=settings.redis_consumer_group,
            consumer_name=consumer_name,
            poll_count=settings.worker_concurrency,
            stop_event=stop_event,
            heartbeat=heartbeat,
        )
    finally:
        await heartbeat.set_status(WorkerStatus.STOPPING)
        stop_event.set()
        await heartbeat_task
        await recovery_task
        async with session_factory() as session:
            await WorkerService(session).mark_offline(worker.id)


if __name__ == "__main__":
    asyncio.run(main())
