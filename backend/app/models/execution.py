import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import ExecutionStatus, NodeExecutionStatus

if TYPE_CHECKING:
    from app.models.log import ExecutionLog
    from app.models.worker import Worker
    from app.models.workflow import Workflow, WorkflowVersion


class Execution(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "executions"
    __table_args__ = (
        Index("ix_executions_status", "status"),
        Index("ix_executions_workflow_version_id", "workflow_version_id"),
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False
    )
    workflow_version_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workflow_versions.id"), nullable=False
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus, name="execution_status", native_enum=False, length=32),
        nullable=False,
        default=ExecutionStatus.CREATED,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triggered_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    workflow: Mapped["Workflow"] = relationship()
    workflow_version: Mapped["WorkflowVersion"] = relationship(back_populates="executions")
    node_executions: Mapped[list["NodeExecution"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )
    logs: Mapped[list["ExecutionLog"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )


class NodeExecution(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "node_executions"
    __table_args__ = (
        UniqueConstraint("execution_id", "node_id"),
        Index("ix_node_executions_execution_id_status", "execution_id", "status"),
        Index("ix_node_executions_idempotency_key", "idempotency_key"),
    )

    execution_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("executions.id"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[NodeExecutionStatus] = mapped_column(
        Enum(NodeExecutionStatus, name="node_execution_status", native_enum=False, length=32),
        nullable=False,
        default=NodeExecutionStatus.PENDING,
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    output_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    redis_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    worker_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workers.id"), nullable=True
    )
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    execution: Mapped["Execution"] = relationship(back_populates="node_executions")
    worker: Mapped["Worker | None"] = relationship(back_populates="node_executions")
    logs: Mapped[list["ExecutionLog"]] = relationship(
        back_populates="node_execution", cascade="all, delete-orphan"
    )
