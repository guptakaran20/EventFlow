"""Seed the database with ready-to-run demo workflows.

Usage:
    python scripts/seed_demo_workflows.py

Creates a dedicated API key to own the demo workflows and prints its raw
value once (store it to call the API). Re-running creates a fresh owner key
and a new set of demo workflows.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import dispose_engine, get_session_factory  # noqa: E402
from app.schemas.workflow import (  # noqa: E402
    Edge,
    Node,
    RetryPolicy,
    WorkflowDefinition,
)
from app.services.api_key_service import APIKeyService  # noqa: E402
from app.services.executor_registry import get_executor_registry  # noqa: E402
from app.services.workflow_service import WorkflowService  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")


DEMO_WORKFLOWS = [
    WorkflowDefinition(
        name="Linear HTTP Demo",
        description="A simple sequence of HTTP requests.",
        nodes=[
            Node(
                id="req1",
                type="http",
                config={"url": "https://jsonplaceholder.typicode.com/todos/1", "method": "GET"},
            ),
            Node(
                id="req2",
                type="http",
                config={"url": "https://jsonplaceholder.typicode.com/todos/2", "method": "GET"},
            ),
        ],
        edges=[Edge(from_node="req1", to_node="req2")],
    ),
    WorkflowDefinition(
        name="Condition Demo",
        description="Branches based on the result of a condition.",
        nodes=[
            Node(
                id="cond1",
                type="condition",
                config={
                    "expression": "input.value > 10",
                    "true_path": "true_path",
                    "false_path": "false_path",
                },
            ),
            Node(
                id="true_path",
                type="http",
                config={"url": "https://httpbin.org/get?result=true", "method": "GET"},
            ),
            Node(
                id="false_path",
                type="http",
                config={"url": "https://httpbin.org/get?result=false", "method": "GET"},
            ),
        ],
        edges=[
            Edge(from_node="cond1", to_node="true_path", condition="true"),
            Edge(from_node="cond1", to_node="false_path", condition="false"),
        ],
    ),
    WorkflowDefinition(
        name="Retry & DLQ Demo",
        description="This node intentionally fails and exhausts its retries.",
        nodes=[
            Node(
                id="failing_node",
                type="http",
                config={"url": "https://httpbin.org/status/500", "method": "GET"},
                retry_policy=RetryPolicy(max_attempts=3),
            ),
        ],
        edges=[],
    ),
    WorkflowDefinition(
        name="Delay Demo",
        description="Pauses execution before continuing.",
        nodes=[
            Node(id="delay1", type="delay", config={"duration_seconds": 10}),
            Node(
                id="after_delay",
                type="http",
                config={"url": "https://httpbin.org/get?delayed=true", "method": "GET"},
            ),
        ],
        edges=[Edge(from_node="delay1", to_node="after_delay")],
    ),
]


async def main() -> None:
    session_factory = get_session_factory()
    registry = get_executor_registry()

    async with session_factory() as session:
        api_key, raw_key = await APIKeyService(session).create("demo-workflows-owner")
        logger.info("Created owner API key '%s' (id=%s)", api_key.name, api_key.id)

        service = WorkflowService(session, registry)
        for definition in DEMO_WORKFLOWS:
            workflow, version = await service.create_workflow(
                name=definition.name,
                description=definition.description,
                definition=definition,
                owner_api_key_id=api_key.id,
            )
            logger.info(
                "Seeded '%s' (id=%s, v%s)",
                workflow.name,
                workflow.id,
                version.version_number,
            )

    await dispose_engine()

    print("\nSuccessfully seeded demo workflows!")
    print(f"Owner API key (shown once, store it now): {raw_key}")


if __name__ == "__main__":
    asyncio.run(main())
