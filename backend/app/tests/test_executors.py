import httpx
import pytest

from app.services.executor_registry import ExecutionContext, HttpExecutor, WebhookExecutor


def _make_context(config: dict, idempotency_key: str = "exec-1:node-1:1") -> ExecutionContext:
    return ExecutionContext(
        execution_id="exec-1",
        node_execution_id="node-exec-1",
        node_id="node-1",
        config=config,
        workflow_input={},
        upstream_outputs={},
        attempt=1,
        idempotency_key=idempotency_key,
    )


@pytest.mark.asyncio
async def test_http_executor_forwards_idempotency_key_header(monkeypatch):
    captured_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.update(request.headers)
        return httpx.Response(200, json={"ok": True})

    original_client = httpx.AsyncClient

    def patched_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    executor = HttpExecutor()
    context = _make_context({"method": "GET", "url": "https://example.com/api"})
    result = await executor.execute(context)

    assert result.success is True
    assert captured_headers.get("idempotency-key") == "exec-1:node-1:1"


@pytest.mark.asyncio
async def test_http_executor_respects_explicit_idempotency_header(monkeypatch):
    captured_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.update(request.headers)
        return httpx.Response(200, json={"ok": True})

    original_client = httpx.AsyncClient

    def patched_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    executor = HttpExecutor()
    context = _make_context(
        {
            "method": "GET",
            "url": "https://example.com/api",
            "headers": {"Idempotency-Key": "custom-key"},
        }
    )
    result = await executor.execute(context)

    assert result.success is True
    assert captured_headers.get("idempotency-key") == "custom-key"


@pytest.mark.asyncio
async def test_webhook_executor_forwards_idempotency_key_header(monkeypatch):
    captured_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.update(request.headers)
        return httpx.Response(200, json={"ok": True})

    original_client = httpx.AsyncClient

    def patched_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    executor = WebhookExecutor()
    context = _make_context({"target_url": "https://example.com/webhook"})
    result = await executor.execute(context)

    assert result.success is True
    assert captured_headers.get("idempotency-key") == "exec-1:node-1:1"


def test_execution_context_idempotency_key_defaults_empty():
    context = ExecutionContext(
        execution_id="exec-1",
        node_execution_id="node-exec-1",
        node_id="node-1",
        config={},
        workflow_input={},
        upstream_outputs={},
        attempt=1,
    )
    assert context.idempotency_key == ""


@pytest.mark.asyncio
async def test_http_executor_blocks_ssrf_loopback():
    executor = HttpExecutor()
    context = _make_context({"method": "GET", "url": "http://127.0.0.1:8000/api"})
    result = await executor.execute(context)
    assert result.success is False
    assert "SSRF Blocked" in result.error


@pytest.mark.asyncio
async def test_http_executor_blocks_ssrf_metadata():
    executor = HttpExecutor()
    context = _make_context({"method": "GET", "url": "http://169.254.169.254/latest/meta-data/"})
    result = await executor.execute(context)
    assert result.success is False
    assert "SSRF Blocked" in result.error


@pytest.mark.asyncio
async def test_webhook_executor_blocks_ssrf():
    executor = WebhookExecutor()
    context = _make_context({"target_url": "http://localhost:5432"})
    result = await executor.execute(context)
    assert result.success is False
    assert "SSRF Blocked" in result.error
