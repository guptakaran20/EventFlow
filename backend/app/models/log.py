import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.enums import LogLevel

if TYPE_CHECKING:
    from app.models.execution import Execution, NodeExecution


class ExecutionLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "execution_logs"
    __table_args__ = (
        Index("ix_execution_logs_execution_id_created_at", "execution_id", "created_at"),
    )

    execution_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("executions.id"), nullable=False
    )
    node_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("node_executions.id"), nullable=True
    )
    level: Mapped[LogLevel] = mapped_column(
        Enum(LogLevel, name="log_level", native_enum=False, length=16),
        nullable=False,
        default=LogLevel.INFO,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    log_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

    execution: Mapped["Execution"] = relationship(back_populates="logs")
    node_execution: Mapped["NodeExecution | None"] = relationship(back_populates="logs")
