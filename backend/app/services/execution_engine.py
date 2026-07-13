import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.enums import ExecutionStatus, NodeExecutionStatus
from app.models.execution import Execution, NodeExecution
from app.models.workflow import Workflow, WorkflowVersion
from app.queue.publisher import QueuePublisher
from app.schemas.workflow import WorkflowDefinition
from app.services.dag_validator import validate_workflow
from app.services.executor_registry import ExecutorRegistry
from app.services.state_transition import StateTransitionService
from app.transport.contracts import (
    ExecutionDTO,
    NodeExecutionDTO,
    StartExecutionCommand,
    TransitionNodeCommand,
)


class ExecutionEngine:
    """Core execution engine logic for Phase 5."""

    def __init__(
        self,
        session: AsyncSession,
        registry: ExecutorRegistry,
        queue_publisher: QueuePublisher,
    ):
        self.session = session
        self.registry = registry
        self.queue_publisher = queue_publisher
        self.state_service = StateTransitionService(session)

    async def start_execution(
        self, command: StartExecutionCommand, owner_api_key_id: uuid.UUID
    ) -> ExecutionDTO:
        # Resolve workflow version
        stmt = (
            select(WorkflowVersion, Workflow)
            .join(Workflow, Workflow.id == WorkflowVersion.workflow_id)
            .where(WorkflowVersion.id == command.workflow_version_id)
        )
        result = await self.session.execute(stmt)
        row = result.first()

        if not row:
            raise AppError("Workflow version not found", code="not_found", status_code=404)

        version, workflow = row

        if workflow.owner_api_key_id != owner_api_key_id:
            raise AppError("Unauthorized access to workflow", code="unauthorized", status_code=403)

        definition = WorkflowDefinition.model_validate(version.definition)

        # Re-validate the DAG to discover root nodes
        validation_result = validate_workflow(definition, self.registry)
        root_nodes = set(validation_result["root_nodes"])

        # Persist Execution record
        execution = Execution(
            workflow_id=workflow.id,
            workflow_version_id=version.id,
            status=ExecutionStatus.CREATED,
            input_payload=command.input_payload,
        )
        self.session.add(execution)
        await self.session.flush()

        # Persist NodeExecution records
        node_executions = []
        for node in definition.nodes:
            node_exec = NodeExecution(
                execution_id=execution.id,
                node_id=node.id,
                node_type=node.type,
                status=NodeExecutionStatus.PENDING,
                attempt=0,
                max_attempts=node.config.get("max_attempts", 1)
                if isinstance(node.config, dict)
                else 1,
            )
            self.session.add(node_exec)
            node_executions.append(node_exec)

        await self.session.flush()

        # Transition execution to RUNNING
        await self.state_service.transition_execution_status(
            execution_id=execution.id,
            from_status=ExecutionStatus.CREATED,
            to_status=ExecutionStatus.RUNNING,
        )

        # Transition root nodes to QUEUED
        for node_exec in node_executions:
            if node_exec.node_id in root_nodes:
                await self.state_service.transition_node_status(
                    node_execution_id=node_exec.id,
                    from_status=NodeExecutionStatus.PENDING,
                    to_status=NodeExecutionStatus.QUEUED,
                )

                message_id = await self.queue_publisher.publish_node_execution(
                    execution_id=execution.id,
                    node_execution_id=node_exec.id,
                    workflow_version_id=version.id,
                    node_id=node_exec.node_id,
                    attempt=node_exec.attempt,
                )
                if message_id:
                    node_exec.redis_message_id = message_id

        await self.session.commit()
        return await self.get_execution(execution.id, owner_api_key_id)

    async def get_execution(
        self, execution_id: uuid.UUID, owner_api_key_id: uuid.UUID
    ) -> ExecutionDTO | None:
        stmt = (
            select(Execution)
            .join(Workflow, Workflow.id == Execution.workflow_id)
            .where(Execution.id == execution_id, Workflow.owner_api_key_id == owner_api_key_id)
        )
        result = await self.session.execute(stmt)
        execution = result.scalar_one_or_none()

        if not execution:
            return None

        node_dtos = await self.get_node_executions(execution_id, owner_api_key_id)

        return ExecutionDTO(
            id=execution.id,
            workflow_id=execution.workflow_id,
            workflow_version_id=execution.workflow_version_id,
            status=execution.status.name,
            input_payload=execution.input_payload,
            error_message=execution.error_message,
            node_executions=node_dtos,
        )

    async def get_node_executions(
        self, execution_id: uuid.UUID, owner_api_key_id: uuid.UUID
    ) -> list[NodeExecutionDTO]:
        # Validate owner
        stmt = (
            select(Execution)
            .join(Workflow, Workflow.id == Execution.workflow_id)
            .where(Execution.id == execution_id, Workflow.owner_api_key_id == owner_api_key_id)
        )
        result = await self.session.execute(stmt)
        if not result.scalar_one_or_none():
            return []

        stmt_nodes = select(NodeExecution).where(NodeExecution.execution_id == execution_id)
        result_nodes = await self.session.execute(stmt_nodes)

        return [
            NodeExecutionDTO(
                id=node.id,
                execution_id=node.execution_id,
                node_id=node.node_id,
                node_type=node.node_type,
                status=node.status.name,
                attempt=node.attempt,
                max_attempts=node.max_attempts,
                input_payload=node.input_payload,
                output_payload=node.output_payload,
                error_message=node.error_message,
            )
            for node in result_nodes.scalars()
        ]

    async def transition_node(self, command: TransitionNodeCommand) -> NodeExecutionDTO:
        raise NotImplementedError("Not required for Phase 5")
