import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import get_settings
from app.db.models import Base
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowVersionCreate,
    NodeDefinition,
    EdgeDefinition,
    HTTPExecutorConfig,
    ConditionExecutorConfig,
    DelayExecutorConfig,
)
from app.services.workflow_service import WorkflowService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    # We will use the admin API key ID from the seeded migrations, if available, or just a dummy UUID.
    # The existing migrations seed: 11111111-1111-1111-1111-111111111111
    owner_id = UUID("11111111-1111-1111-1111-111111111111")
    
    async with session_factory() as session:
        service = WorkflowService(session)
        
        # 1. Linear HTTP Workflow
        logger.info("Creating Linear HTTP Workflow...")
        await service.create_workflow(
            owner_id,
            WorkflowCreate(
                name="Linear HTTP Demo",
                description="A simple sequence of HTTP requests.",
            )
        )
        # Fetch it to get the ID (Assuming name is unique for demo purposes, or we just fetch the latest)
        # For simplicity, we can just insert and not worry about ID if we don't need it, but we need it to add a version.
        workflows = await service.list_workflows(owner_id)
        linear_wf = next((w for w in workflows if w.name == "Linear HTTP Demo"), None)
        if linear_wf:
            await service.create_version(
                linear_wf.id,
                owner_id,
                WorkflowVersionCreate(
                    nodes=[
                        NodeDefinition(id="req1", type="http", config=HTTPExecutorConfig(url="https://jsonplaceholder.typicode.com/todos/1", method="GET")),
                        NodeDefinition(id="req2", type="http", config=HTTPExecutorConfig(url="https://jsonplaceholder.typicode.com/todos/2", method="GET")),
                    ],
                    edges=[
                        EdgeDefinition(source="req1", target="req2"),
                    ]
                )
            )

        # 2. Condition Workflow
        logger.info("Creating Condition Workflow...")
        await service.create_workflow(
            owner_id,
            WorkflowCreate(
                name="Condition Demo",
                description="Branches based on the status of a condition.",
            )
        )
        workflows = await service.list_workflows(owner_id)
        cond_wf = next((w for w in workflows if w.name == "Condition Demo"), None)
        if cond_wf:
            await service.create_version(
                cond_wf.id,
                owner_id,
                WorkflowVersionCreate(
                    nodes=[
                        NodeDefinition(id="cond1", type="condition", config=ConditionExecutorConfig(condition_expression="$.input.value > 10")),
                        NodeDefinition(id="true_path", type="http", config=HTTPExecutorConfig(url="https://httpbin.org/get?result=true", method="GET")),
                        NodeDefinition(id="false_path", type="http", config=HTTPExecutorConfig(url="https://httpbin.org/get?result=false", method="GET")),
                    ],
                    edges=[
                        EdgeDefinition(source="cond1", target="true_path", condition="true"),
                        EdgeDefinition(source="cond1", target="false_path", condition="false"),
                    ]
                )
            )

        # 3. Retry-to-DLQ Workflow
        logger.info("Creating Retry-to-DLQ Workflow...")
        await service.create_workflow(
            owner_id,
            WorkflowCreate(
                name="Retry & DLQ Demo",
                description="This node intentionally fails and uses max retries.",
            )
        )
        workflows = await service.list_workflows(owner_id)
        retry_wf = next((w for w in workflows if w.name == "Retry & DLQ Demo"), None)
        if retry_wf:
            await service.create_version(
                retry_wf.id,
                owner_id,
                WorkflowVersionCreate(
                    nodes=[
                        NodeDefinition(
                            id="failing_node", 
                            type="http", 
                            config=HTTPExecutorConfig(url="https://httpbin.org/status/500", method="GET"),
                            max_attempts=3
                        ),
                    ],
                    edges=[]
                )
            )

        # 4. Delay Workflow
        logger.info("Creating Delay Workflow...")
        await service.create_workflow(
            owner_id,
            WorkflowCreate(
                name="Delay Demo",
                description="Pauses execution before continuing.",
            )
        )
        workflows = await service.list_workflows(owner_id)
        delay_wf = next((w for w in workflows if w.name == "Delay Demo"), None)
        if delay_wf:
            await service.create_version(
                delay_wf.id,
                owner_id,
                WorkflowVersionCreate(
                    nodes=[
                        NodeDefinition(id="delay1", type="delay", config=DelayExecutorConfig(delay_seconds=10)),
                        NodeDefinition(id="after_delay", type="http", config=HTTPExecutorConfig(url="https://httpbin.org/get?delayed=true", method="GET")),
                    ],
                    edges=[
                        EdgeDefinition(source="delay1", target="after_delay"),
                    ]
                )
            )

        logger.info("Successfully seeded demo workflows!")

if __name__ == "__main__":
    asyncio.run(main())
