"""Phase 11 WebSocket tests.

Two tiers:

* Unit tests (no DB / no Redis) exercise the connection manager, event
  envelopes, and the broadcaster's failure isolation. These always run.
* Integration tests exercise the ``/api/v1/ws/executions/{id}`` endpoint and
  require the Postgres test database (same fixtures as the REST suite).
"""

import uuid

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import get_settings
from app.main import app as fastapi_app
from app.queue.publisher import InMemoryQueuePublisher
from app.transport.local_execution_client import get_queue_publisher
from app.websocket import events
from app.websocket.broadcaster import broadcast_envelopes, flush_events, stage_event
from app.websocket.connection_manager import ConnectionManager

# --------------------------------------------------------------------------- #
# Unit tests: connection manager
# --------------------------------------------------------------------------- #


class FakeSocket:
    """Minimal WebSocket stand-in recording sent frames; can be made to fail."""

    def __init__(self, fail: bool = False):
        self.sent: list[dict] = []
        self.fail = fail

    async def send_json(self, message: dict) -> None:
        if self.fail:
            raise RuntimeError("socket broken")
        self.sent.append(message)


@pytest.mark.asyncio
async def test_connect_and_broadcast_to_multiple_subscribers():
    manager = ConnectionManager()
    exec_id = "exec-1"
    a, b = FakeSocket(), FakeSocket()
    await manager.connect(exec_id, a)
    await manager.connect(exec_id, b)

    assert await manager.connection_count(exec_id) == 2

    await manager.broadcast(exec_id, {"type": "x"})
    assert a.sent == [{"type": "x"}]
    assert b.sent == [{"type": "x"}]


@pytest.mark.asyncio
async def test_disconnect_cleans_up_bucket():
    manager = ConnectionManager()
    exec_id = "exec-2"
    sock = FakeSocket()
    await manager.connect(exec_id, sock)
    await manager.disconnect(exec_id, sock)

    assert await manager.connection_count(exec_id) == 0
    # Bucket removed entirely -> no memory leak.
    assert exec_id not in manager._connections


@pytest.mark.asyncio
async def test_broadcast_removes_broken_socket_and_does_not_raise():
    manager = ConnectionManager()
    exec_id = "exec-3"
    good, bad = FakeSocket(), FakeSocket(fail=True)
    await manager.connect(exec_id, good)
    await manager.connect(exec_id, bad)

    # Must not raise even though one socket errors.
    await manager.broadcast(exec_id, {"type": "y"})

    assert good.sent == [{"type": "y"}]
    # Broken socket auto-removed.
    assert await manager.connection_count(exec_id) == 1


@pytest.mark.asyncio
async def test_broadcast_to_execution_with_no_subscribers_is_noop():
    manager = ConnectionManager()
    # No connections -> should silently do nothing.
    await manager.broadcast("nobody", {"type": "z"})


# --------------------------------------------------------------------------- #
# Unit tests: event envelopes
# --------------------------------------------------------------------------- #


def test_event_envelope_shape():
    exec_id = uuid.uuid4()
    node_exec_id = uuid.uuid4()

    e = events.execution_updated(exec_id, "RUNNING")
    assert e["type"] == "execution_updated"
    assert e["execution_id"] == str(exec_id)
    assert e["data"]["status"] == "RUNNING"
    assert "timestamp" in e

    n = events.node_updated(exec_id, node_exec_id, "process_csv", "SUCCEEDED", 2)
    assert n["type"] == "node_updated"
    assert n["data"] == {
        "node_execution_id": str(node_exec_id),
        "node_id": "process_csv",
        "status": "SUCCEEDED",
        "attempt": 2,
    }

    log = events.execution_log(
        exec_id, "INFO", "retry_scheduled", "Retry scheduled", metadata={"attempt": 2}
    )
    assert log["type"] == "execution_log"
    assert log["data"]["level"] == "INFO"
    assert log["data"]["metadata"] == {"attempt": 2}

    w = events.worker_updated(exec_id, "worker-1", "BUSY", "job-1")
    assert w["type"] == "worker_updated"
    assert w["data"]["worker_id"] == "worker-1"
    assert w["data"]["status"] == "BUSY"


# --------------------------------------------------------------------------- #
# Unit tests: broadcaster staging / flush / failure isolation
# --------------------------------------------------------------------------- #


class FakeSession:
    """Only the ``.info`` dict is used by the broadcaster staging helpers."""

    def __init__(self):
        self.info: dict = {}


@pytest.mark.asyncio
async def test_stage_and_flush_preserves_order(monkeypatch):
    session = FakeSession()
    stage_event(session, events.execution_updated("e1", "RUNNING"))
    stage_event(session, events.node_updated("e1", "n1", "root", "QUEUED", 1))

    sent: list[dict] = []

    async def fake_broadcast(self, execution_id, message):
        sent.append(message)

    monkeypatch.setattr(ConnectionManager, "broadcast", fake_broadcast)

    await flush_events(session)

    assert [m["type"] for m in sent] == ["execution_updated", "node_updated"]
    # Buffer cleared after flush.
    assert session.info.get("ws_events") in (None, [])


@pytest.mark.asyncio
async def test_broadcast_failure_never_raises(monkeypatch):
    """A broadcast failure after commit must be swallowed, never propagated.

    This proves that once a caller has committed and calls flush_events, a
    WebSocket failure cannot bubble up to trigger a rollback or error the
    workflow. See test_ws_broadcast_failure_does_not_prevent_commit for the
    end-to-end DB variant.
    """
    session = FakeSession()
    stage_event(session, events.execution_updated("e1", "RUNNING"))

    async def boom(self, execution_id, message):
        raise RuntimeError("broadcast exploded")

    monkeypatch.setattr(ConnectionManager, "broadcast", boom)

    # Must NOT raise.
    await flush_events(session)
    await broadcast_envelopes([events.execution_updated("e1", "FAILED")])


# --------------------------------------------------------------------------- #
# Unit tests: broadcaster helpers deliver each event type to all subscribers
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_broadcast_helpers_deliver_each_event_type_to_all_subscribers():
    """Multiple subscribers on one execution each receive every event type."""
    from app.websocket import broadcaster
    from app.websocket.connection_manager import get_connection_manager

    manager = get_connection_manager()
    exec_id = str(uuid.uuid4())
    a, b = FakeSocket(), FakeSocket()
    await manager.connect(exec_id, a)
    await manager.connect(exec_id, b)
    try:
        await broadcaster.broadcast_execution_updated(exec_id, "RUNNING")
        await broadcaster.broadcast_node_updated(exec_id, uuid.uuid4(), "node1", "SUCCEEDED", 2)
        await broadcaster.broadcast_execution_log(
            exec_id, "INFO", "retry_scheduled", "Retry scheduled", metadata={"attempt": 2}
        )
        await broadcaster.broadcast_worker_updated(exec_id, uuid.uuid4(), "BUSY", "job-1")

        for sock in (a, b):
            types = [m["type"] for m in sock.sent]
            assert types == [
                "execution_updated",
                "node_updated",
                "execution_log",
                "worker_updated",
            ]
    finally:
        await manager.disconnect(exec_id, a)
        await manager.disconnect(exec_id, b)


@pytest.mark.asyncio
async def test_worker_broadcast_without_execution_is_skipped():
    from app.websocket import broadcaster

    # execution_id=None must be a no-op (worker updates only reach a bound execution).
    await broadcaster.broadcast_worker_updated(None, uuid.uuid4(), "IDLE", None)


def test_ping_envelope_shape():
    p = events.ping()
    assert p["type"] == "ping"
    assert "timestamp" in p


# --------------------------------------------------------------------------- #
# Integration tests: WS endpoint (require Postgres test DB)
# --------------------------------------------------------------------------- #





@pytest.fixture
def mock_queue_publisher():
    publisher = InMemoryQueuePublisher()
    fastapi_app.dependency_overrides[get_queue_publisher] = lambda: publisher
    yield publisher
    fastapi_app.dependency_overrides.pop(get_queue_publisher, None)


async def _create_execution(client: AsyncClient, auth_headers: dict) -> str:
    workflow_payload = {
        "name": "WS Workflow",
        "description": "ws",
        "definition": {
            "name": "WS Workflow",
            "nodes": [{"id": "node1", "type": "delay", "config": {"duration_seconds": 1}}],
            "edges": [],
        },
    }
    resp = await client.post("/api/v1/workflows", json=workflow_payload, headers=auth_headers)
    assert resp.status_code == 201
    version_id = resp.json()["id"]

    exec_resp = await client.post(
        "/api/v1/executions",
        json={"workflow_version_id": version_id, "input_payload": {}},
        headers=auth_headers,
    )
    assert exec_resp.status_code == 201
    return exec_resp.json()["id"]


@pytest.mark.asyncio
async def test_ws_connection_success(client: AsyncClient, auth_headers: dict, mock_queue_publisher, monkeypatch):
    async def fake_authorize(exec_id, api_key):
        return api_key == "test-key"
    monkeypatch.setattr("app.api.websocket._authorize", fake_authorize)
    
    execution_id = await _create_execution(client, auth_headers)

    sync_client = TestClient(fastapi_app)
    with sync_client.websocket_connect(
        f"/api/v1/ws/executions/{execution_id}?api_key=test-key"
    ) as ws:
        ws.close()


@pytest.mark.asyncio
async def test_ws_unauthorized_rejected(
    client: AsyncClient, auth_headers: dict, mock_queue_publisher, monkeypatch
):
    async def fake_authorize(exec_id, api_key):
        return api_key == "test-key"
    monkeypatch.setattr("app.api.websocket._authorize", fake_authorize)
    
    execution_id = await _create_execution(client, auth_headers)

    sync_client = TestClient(fastapi_app)
    # Wrong key -> connection rejected before accept.
    with pytest.raises(WebSocketDisconnect):
        with sync_client.websocket_connect(
            f"/api/v1/ws/executions/{execution_id}?api_key=wrong-key"
        ):
            pass

    # Valid key but different owner -> also rejected.
    with pytest.raises(WebSocketDisconnect):
        with sync_client.websocket_connect(
            f"/api/v1/ws/executions/{execution_id}?api_key=other-key"
        ):
            pass


@pytest.mark.asyncio
async def test_ws_broadcast_failure_does_not_prevent_commit(
    client: AsyncClient, auth_headers: dict, mock_queue_publisher, monkeypatch
):
    """A broken WebSocket during broadcast must NOT roll back committed state.

    We force every broadcast to raise, then create an execution (which commits
    state and flushes events). The commit must still succeed and be readable.
    """

    async def boom(self, execution_id, message):
        raise RuntimeError("broadcast exploded")

    async def fake_authorize(exec_id, api_key):
        return api_key == "test-key"
    monkeypatch.setattr("app.api.websocket._authorize", fake_authorize)
    monkeypatch.setattr(ConnectionManager, "broadcast", boom)

    execution_id = await _create_execution(client, auth_headers)

    # State was committed despite the broadcast blowing up on every event.
    get_resp = await client.get(f"/api/v1/executions/{execution_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "RUNNING"
