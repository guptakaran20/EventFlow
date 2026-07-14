import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import WorkerStatus


class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    worker_id: uuid.UUID
    hostname: str
    status: WorkerStatus
    last_heartbeat_at: datetime | None
    current_job_id: str | None
    started_at: datetime

    @classmethod
    def from_worker(cls, worker) -> "WorkerResponse":
        hostname = (worker.worker_metadata or {}).get("hostname", "unknown")
        return cls(
            worker_id=worker.id,
            hostname=hostname,
            status=worker.status,
            last_heartbeat_at=worker.last_heartbeat_at,
            current_job_id=worker.current_job_id,
            started_at=worker.created_at,
        )
