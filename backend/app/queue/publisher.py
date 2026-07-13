import uuid
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import ResponseError


class QueuePayload(dict):
    """Payload for queueing a node execution job."""

    pass


def serialize_job_payload(
    execution_id: uuid.UUID,
    node_execution_id: uuid.UUID,
    workflow_version_id: uuid.UUID,
    node_id: str,
    attempt: int,
) -> dict[str, str]:
    """Serialize a node execution job into Redis Stream string fields."""
    return {
        "execution_id": str(execution_id),
        "node_execution_id": str(node_execution_id),
        "workflow_version_id": str(workflow_version_id),
        "node_id": node_id,
        "attempt": str(attempt),
    }


def deserialize_job_payload(fields: dict[str, str]) -> dict:
    """Deserialize Redis Stream string fields back into typed job values."""
    return {
        "execution_id": uuid.UUID(fields["execution_id"]),
        "node_execution_id": uuid.UUID(fields["node_execution_id"]),
        "workflow_version_id": uuid.UUID(fields["workflow_version_id"]),
        "node_id": fields["node_id"],
        "attempt": int(fields["attempt"]),
    }


class QueuePublisher(Protocol):
    async def publish_node_execution(
        self,
        execution_id: uuid.UUID,
        node_execution_id: uuid.UUID,
        workflow_version_id: uuid.UUID,
        node_id: str,
        attempt: int,
    ) -> str | None:
        """Publish a node execution job to the queue. Returns the queue message ID, if any."""
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
    ) -> str | None:
        payload = {
            "execution_id": str(execution_id),
            "node_execution_id": str(node_execution_id),
            "workflow_version_id": str(workflow_version_id),
            "node_id": node_id,
            "attempt": attempt,
        }
        self.published_jobs.append(payload)
        return None


class RedisStreamQueuePublisher:
    """Redis Streams-backed queue publisher.

    Redis is the job delivery mechanism only; PostgreSQL remains the
    source of truth for execution/node state.
    """

    def __init__(self, redis: Redis, stream_name: str, consumer_group: str):
        self.redis = redis
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self._group_ready = False

    async def ensure_consumer_group(self) -> None:
        """Idempotently create the consumer group (and stream) if missing."""
        if self._group_ready:
            return
        try:
            await self.redis.xgroup_create(
                name=self.stream_name, groupname=self.consumer_group, id="0", mkstream=True
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        self._group_ready = True

    async def publish_node_execution(
        self,
        execution_id: uuid.UUID,
        node_execution_id: uuid.UUID,
        workflow_version_id: uuid.UUID,
        node_id: str,
        attempt: int,
    ) -> str:
        await self.ensure_consumer_group()
        fields = serialize_job_payload(
            execution_id, node_execution_id, workflow_version_id, node_id, attempt
        )
        return await self.redis.xadd(self.stream_name, fields)

    async def queue_depth(self) -> int:
        """Approximate queue depth via XLEN. Prefer PostgreSQL state for dashboards."""
        return await self.redis.xlen(self.stream_name)
