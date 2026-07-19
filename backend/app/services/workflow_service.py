import hashlib
import json
import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.db.session import get_db_session
from app.models.workflow import Workflow, WorkflowVersion
from app.schemas.workflow import WorkflowDefinition
from app.services.dag_validator import validate_workflow
from app.services.executor_registry import ExecutorRegistry, get_executor_registry


class WorkflowService:
    def __init__(self, db: AsyncSession, registry: ExecutorRegistry):
        self._db = db
        self._registry = registry

    def _generate_checksum(self, definition: WorkflowDefinition) -> str:
        # Canonical JSON serialization for deterministic checksum
        payload = definition.model_dump(exclude_none=True)
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    async def create_workflow(
        self,
        name: str,
        description: str,
        definition: WorkflowDefinition,
        owner_api_key_id: uuid.UUID,
    ) -> tuple[Workflow, WorkflowVersion]:
        # Validate the definition DAG
        validation_result = validate_workflow(definition, self._registry)
        if not validation_result["valid"]:
            # Should not happen if endpoints are properly calling validation before
            # but we do it here to ensure integrity. Actually, let's just validate.
            raise AppError("Invalid workflow definition", code="invalid_workflow")

        checksum = self._generate_checksum(definition)

        workflow = Workflow(
            owner_api_key_id=owner_api_key_id,
            name=name,
            description=description,
        )
        self._db.add(workflow)

        # Flush to get workflow.id
        await self._db.flush()

        version = WorkflowVersion(
            workflow_id=workflow.id,
            version_number=1,
            definition=definition.model_dump(exclude_none=True, mode="json"),
            checksum=checksum,
        )
        self._db.add(version)

        await self._db.commit()
        await self._db.refresh(workflow)
        await self._db.refresh(version)

        return workflow, version

    async def list_workflows(
        self, owner_api_key_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> Sequence[tuple[Workflow, int]]:
        """List workflows for an owner along with their latest version number."""
        stmt = (
            select(
                Workflow, func.max(WorkflowVersion.version_number).label("latest_version_number")
            )
            .outerjoin(WorkflowVersion, Workflow.id == WorkflowVersion.workflow_id)
            .where(Workflow.owner_api_key_id == owner_api_key_id)
            .group_by(Workflow.id)
            .order_by(Workflow.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._db.execute(stmt)
        return result.all()  # returns list of (Workflow, int)

    async def get_workflow(
        self, workflow_id: uuid.UUID, owner_api_key_id: uuid.UUID
    ) -> Workflow | None:
        """Get workflow detail including all versions."""
        stmt = (
            select(Workflow)
            .options(selectinload(Workflow.versions))
            .where(Workflow.id == workflow_id, Workflow.owner_api_key_id == owner_api_key_id)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_workflow_version(
        self,
        workflow_id: uuid.UUID,
        definition: WorkflowDefinition,
        owner_api_key_id: uuid.UUID,
    ) -> WorkflowVersion:
        # First ensure the workflow exists and belongs to the owner
        stmt = select(Workflow).where(
            Workflow.id == workflow_id, Workflow.owner_api_key_id == owner_api_key_id
        )
        result = await self._db.execute(stmt)
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise AppError("Workflow not found", code="not_found", status_code=404)

        # Validate DAG
        validation_result = validate_workflow(definition, self._registry)
        if not validation_result["valid"]:
            raise AppError("Invalid workflow definition", code="invalid_workflow")

        # Get the latest version number
        max_v_stmt = select(func.max(WorkflowVersion.version_number)).where(
            WorkflowVersion.workflow_id == workflow_id
        )
        max_v_result = await self._db.execute(max_v_stmt)
        max_v = max_v_result.scalar() or 0
        new_version_number = max_v + 1

        checksum = self._generate_checksum(definition)

        version = WorkflowVersion(
            workflow_id=workflow_id,
            version_number=new_version_number,
            definition=definition.model_dump(exclude_none=True, mode="json"),
            checksum=checksum,
        )

        # We should update workflow's updated_at timestamp as well
        workflow.updated_at = func.now()

        self._db.add(version)
        await self._db.commit()
        await self._db.refresh(version)

        return version

    async def delete_workflow(
        self, workflow_id: uuid.UUID, owner_api_key_id: uuid.UUID
    ) -> bool:
        stmt = select(Workflow).where(
            Workflow.id == workflow_id, Workflow.owner_api_key_id == owner_api_key_id
        )
        result = await self._db.execute(stmt)
        workflow = result.scalar_one_or_none()
        if not workflow:
            return False

        await self._db.delete(workflow)
        await self._db.commit()
        return True


async def get_workflow_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    registry: Annotated[ExecutorRegistry, Depends(get_executor_registry)],
) -> WorkflowService:
    return WorkflowService(db, registry)
