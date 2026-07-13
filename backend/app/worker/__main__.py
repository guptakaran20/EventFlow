import asyncio
import logging
import os
import socket
import uuid

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.queue.publisher import InMemoryQueuePublisher, QueuePublisher, RedisStreamQueuePublisher
from app.queue.redis_client import get_redis
from app.services.executor_registry import get_executor_registry
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
    consumer_name = f"worker-{socket.gethostname()}-{os.getpid()}-{uuid.uuid4()}"
    logger.info("starting worker %s", consumer_name)

    await run_worker(
        session_factory=get_session_factory(),
        registry=get_executor_registry(),
        queue_publisher=_build_queue_publisher(settings),
        redis=get_redis(),
        stream_name=settings.redis_stream_name,
        consumer_group=settings.redis_consumer_group,
        consumer_name=consumer_name,
    )


if __name__ == "__main__":
    asyncio.run(main())
