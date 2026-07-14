import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import WorkerStatus


class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    worker_id: uuid.UUID
    hostname: str
    status: WorkerStatus
    current_job_id: str | None
    started_at: datetime
    last_heartbeat_at: datetime | None
    heartbeat_age_seconds: float | None

    @classmethod
    def from_worker(cls, worker) -> "WorkerResponse":
        hostname = (worker.worker_metadata or {}).get("hostname", "unknown")
        heartbeat_age_seconds = None
        if worker.last_heartbeat_at is not None:
            heartbeat_age_seconds = (datetime.now(UTC) - worker.last_heartbeat_at).total_seconds()
        return cls(
            worker_id=worker.id,
            hostname=hostname,
            status=worker.status,
            current_job_id=worker.current_job_id,
            started_at=worker.created_at,
            last_heartbeat_at=worker.last_heartbeat_at,
            heartbeat_age_seconds=heartbeat_age_seconds,
        )
