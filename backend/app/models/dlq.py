import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.execution import Execution, NodeExecution


class DeadLetterJob(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "dead_letter_jobs"
    __table_args__ = (Index("ix_dead_letter_jobs_resolved_at", "resolved_at"),)

    execution_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("executions.id"), nullable=False
    )
    node_execution_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("node_executions.id"), nullable=False
    )
    redis_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(String, nullable=True)

    execution: Mapped["Execution"] = relationship()
    node_execution: Mapped["NodeExecution"] = relationship()
