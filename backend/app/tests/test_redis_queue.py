import uuid

import pytest
from redis.exceptions import ResponseError

from app.queue.publisher import (
    InMemoryQueuePublisher,
    RedisStreamQueuePublisher,
    deserialize_job_payload,
    serialize_job_payload,
)


class FakeRedis:
    """Minimal in-memory stand-in for redis.asyncio.Redis, no real Redis needed."""

    def __init__(self):
        self.streams: dict[str, list[tuple[str, dict]]] = {}
        self.groups: dict[str, set[str]] = {}
        self._counter = 0

    async def xgroup_create(self, name, groupname, id="0", mkstream=False):
        self.streams.setdefault(name, [])
        groups = self.groups.setdefault(name, set())
        if groupname in groups:
            raise ResponseError("BUSYGROUP Consumer Group name already exists")
        groups.add(groupname)

    async def xadd(self, name, fields):
        self._counter += 1
        message_id = f"{self._counter}-0"
        self.streams.setdefault(name, []).append((message_id, dict(fields)))
        return message_id

    async def xlen(self, name):
        return len(self.streams.get(name, []))


def test_serialize_deserialize_round_trip():
    execution_id = uuid.uuid4()
    node_execution_id = uuid.uuid4()
    workflow_version_id = uuid.uuid4()

    fields = serialize_job_payload(execution_id, node_execution_id, workflow_version_id, "node1", 2)
    assert all(isinstance(v, str) for v in fields.values())

    restored = deserialize_job_payload(fields)
    assert restored == {
        "execution_id": execution_id,
        "node_execution_id": node_execution_id,
        "workflow_version_id": workflow_version_id,
        "node_id": "node1",
        "attempt": 2,
    }


@pytest.mark.asyncio
async def test_ensure_consumer_group_idempotent():
    redis = FakeRedis()
    publisher = RedisStreamQueuePublisher(redis, "eventflow:jobs", "eventflow-workers")

    await publisher.ensure_consumer_group()
    await publisher.ensure_consumer_group()

    assert redis.groups["eventflow:jobs"] == {"eventflow-workers"}


@pytest.mark.asyncio
async def test_publish_writes_to_stream_and_returns_message_id():
    redis = FakeRedis()
    publisher = RedisStreamQueuePublisher(redis, "eventflow:jobs", "eventflow-workers")

    execution_id = uuid.uuid4()
    node_execution_id = uuid.uuid4()
    workflow_version_id = uuid.uuid4()

    message_id = await publisher.publish_node_execution(
        execution_id=execution_id,
        node_execution_id=node_execution_id,
        workflow_version_id=workflow_version_id,
        node_id="node1",
        attempt=1,
    )

    assert message_id == "1-0"
    assert len(redis.streams["eventflow:jobs"]) == 1
    stored_id, fields = redis.streams["eventflow:jobs"][0]
    assert stored_id == message_id
    assert fields["node_id"] == "node1"
    assert deserialize_job_payload(fields)["execution_id"] == execution_id


@pytest.mark.asyncio
async def test_queue_depth_helper():
    redis = FakeRedis()
    publisher = RedisStreamQueuePublisher(redis, "eventflow:jobs", "eventflow-workers")

    assert await publisher.queue_depth() == 0

    await publisher.publish_node_execution(
        execution_id=uuid.uuid4(),
        node_execution_id=uuid.uuid4(),
        workflow_version_id=uuid.uuid4(),
        node_id="node1",
        attempt=1,
    )
    await publisher.publish_node_execution(
        execution_id=uuid.uuid4(),
        node_execution_id=uuid.uuid4(),
        workflow_version_id=uuid.uuid4(),
        node_id="node2",
        attempt=1,
    )

    assert await publisher.queue_depth() == 2


@pytest.mark.asyncio
async def test_in_memory_publisher_still_works():
    publisher = InMemoryQueuePublisher()
    result = await publisher.publish_node_execution(
        execution_id=uuid.uuid4(),
        node_execution_id=uuid.uuid4(),
        workflow_version_id=uuid.uuid4(),
        node_id="node1",
        attempt=1,
    )
    assert result is None
    assert len(publisher.published_jobs) == 1
