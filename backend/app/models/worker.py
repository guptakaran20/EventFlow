from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import WorkerStatus

if TYPE_CHECKING:
    from app.models.execution import NodeExecution


class Worker(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workers"
    __table_args__ = (Index("ix_workers_last_heartbeat_at", "last_heartbeat_at"),)

    worker_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[WorkerStatus] = mapped_column(
        Enum(WorkerStatus, name="worker_status", native_enum=False, length=32),
        nullable=False,
        default=WorkerStatus.OFFLINE,
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    worker_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

    node_executions: Mapped[list["NodeExecution"]] = relationship(back_populates="worker")
