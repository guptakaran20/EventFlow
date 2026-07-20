import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.enums import WorkerStatus
from app.models.worker import Worker


async def test_metrics():
    session_factory = get_session_factory()
    async with session_factory() as db:
        now = datetime.now(UTC)
        workers_stmt = select(Worker)
        workers_list = (await db.execute(workers_stmt)).scalars().all()

        active_workers = 0
        for w in workers_list:
            if w.status == WorkerStatus.OFFLINE:
                continue
            is_stale = False
            if w.last_heartbeat_at:
                age = (now - w.last_heartbeat_at.replace(tzinfo=UTC)).total_seconds()
                if age > 30:
                    is_stale = True

            ACTIVE_WORKER_STATUSES = (WorkerStatus.IDLE, WorkerStatus.BUSY, WorkerStatus.STARTING)
            if not is_stale and w.status in ACTIVE_WORKER_STATUSES:
                active_workers += 1

        print("Active workers calculated:", active_workers)


if __name__ == "__main__":
    asyncio.run(test_metrics())
