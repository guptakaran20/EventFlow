import asyncio
import logging

from app.core.config import get_settings
from app.worker.background import start_background_worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker_main")


async def main():
    settings = get_settings()
    logger.info(
        f"Starting standalone worker process '{settings.worker_name}' with concurrency {settings.worker_concurrency}..."
    )
    try:
        await start_background_worker()
    except asyncio.CancelledError:
        logger.info("Worker process shutting down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
