import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DeadLetterJobResponse(BaseModel):
    id: uuid.UUID
    execution_id: uuid.UUID
    node_execution_id: uuid.UUID
    redis_message_id: str | None = None
    reason: str
    attempts: int
    payload: dict[str, Any] | None = None
    created_at: datetime
    resolved_at: datetime | None = None
    resolution_note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ResolveDlqRequest(BaseModel):
    resolution_note: str | None = None
