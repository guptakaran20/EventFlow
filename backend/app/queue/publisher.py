import uuid
from typing import Protocol


class QueuePayload(dict):
    """Payload for queueing a node execution job."""

    pass


class QueuePublisher(Protocol):
    async def publish_node_execution(
        self,
        execution_id: uuid.UUID,
        node_execution_id: uuid.UUID,
        workflow_version_id: uuid.UUID,
        node_id: str,
        attempt: int,
    ) -> None:
        """Publish a node execution job to the queue."""
        ...


class InMemoryQueuePublisher:
    """Fake/in-memory queue publisher for testing and MVP without Redis."""

    def __init__(self):
        self.published_jobs: list[dict] = []

    async def publish_node_execution(
        self,
        execution_id: uuid.UUID,
        node_execution_id: uuid.UUID,
        workflow_version_id: uuid.UUID,
        node_id: str,
        attempt: int,
    ) -> None:
        payload = {
            "execution_id": str(execution_id),
            "node_execution_id": str(node_execution_id),
            "workflow_version_id": str(workflow_version_id),
            "node_id": node_id,
            "attempt": attempt,
        }
        self.published_jobs.append(payload)
