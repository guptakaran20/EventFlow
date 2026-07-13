import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.core.errors import AppError

logger = logging.getLogger("app.executors")


@dataclass
class ExecutionContext:
    """Input available to an executor when running a node."""

    execution_id: Any
    node_execution_id: Any
    node_id: str
    config: dict[str, Any]
    workflow_input: dict[str, Any]
    upstream_outputs: dict[str, Any]
    attempt: int


@dataclass
class ExecutorResult:
    """Normalized outcome of running an executor."""

    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


_COMPARISON_RE = re.compile(r"^\s*([\w.]+)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*$")


def _resolve_path(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def _parse_literal(raw: str) -> Any:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw.strip("'\"")


def evaluate_condition_expression(expression: str, data: dict[str, Any]) -> bool:
    """Safely evaluate a simple `path operator literal` expression. No eval/exec."""
    match = _COMPARISON_RE.match(expression)
    if not match:
        raise AppError(f"Unsupported condition expression: {expression}", code="invalid_expression")

    left_path, operator, right_raw = match.groups()
    left = _resolve_path(data, left_path)
    right = _parse_literal(right_raw)

    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    if operator == ">":
        return left > right
    if operator == "<":
        return left < right
    if operator == ">=":
        return left >= right
    return left <= right


class Executor(Protocol):
    type: str

    def validate_config(self, config: dict[str, Any]) -> None: ...

    async def execute(self, context: ExecutionContext) -> ExecutorResult: ...


class HttpExecutor:
    type = "http"

    def validate_config(self, config: dict[str, Any]) -> None:
        if "url" not in config:
            raise AppError("Missing 'url' in http executor config", code="invalid_executor_config")
        if not isinstance(config["url"], str) or not config["url"].startswith(
            ("http://", "https://")
        ):
            raise AppError("Invalid 'url' in http executor config", code="invalid_executor_config")

    async def execute(self, context: ExecutionContext) -> ExecutorResult:
        config = context.config
        timeout = config.get("timeout_seconds", 10)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    config.get("method", "GET").upper(),
                    config["url"],
                    headers=config.get("headers") or {},
                    params=config.get("query"),
                    json=config.get("body"),
                )
        except httpx.HTTPError as exc:
            logger.warning("http executor request failed for node %s", context.node_id)
            return ExecutorResult(success=False, error=str(exc))

        if response.status_code >= 400:
            return ExecutorResult(
                success=False, error=f"HTTP {response.status_code}: {response.text[:200]}"
            )
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text
        return ExecutorResult(
            success=True, output={"status_code": response.status_code, "body": body}
        )


class DelayExecutor:
    type = "delay"

    def validate_config(self, config: dict[str, Any]) -> None:
        if "duration_seconds" not in config:
            raise AppError(
                "Missing 'duration_seconds' in delay executor config",
                code="invalid_executor_config",
            )
        duration = config["duration_seconds"]
        if not isinstance(duration, (int, float)) or duration <= 0:
            raise AppError(
                "'duration_seconds' must be a positive number",
                code="invalid_executor_config",
            )

    async def execute(self, context: ExecutionContext) -> ExecutorResult:
        duration = context.config["duration_seconds"]
        await asyncio.sleep(duration)
        return ExecutorResult(success=True, output={"slept_seconds": duration})


class ConditionExecutor:
    type = "condition"

    def validate_config(self, config: dict[str, Any]) -> None:
        for field_name in ["expression", "true_path", "false_path"]:
            if field_name not in config:
                raise AppError(
                    f"Missing '{field_name}' in condition executor config",
                    code="invalid_executor_config",
                )

        # Simple safeguard to prevent eval-like expressions
        expr = config["expression"]
        if not isinstance(expr, str):
            raise AppError("'expression' must be a string", code="invalid_executor_config")

        # Check for disallowed words typically used in exploits (just a stub validation for now)
        if re.search(r"(import|exec|eval|os|sys|open)", expr):
            raise AppError("Unsafe expression detected", code="invalid_executor_config")

    async def execute(self, context: ExecutionContext) -> ExecutorResult:
        data = {"input": context.workflow_input, "upstream": context.upstream_outputs}
        try:
            result = evaluate_condition_expression(context.config["expression"], data)
        except AppError as exc:
            return ExecutorResult(success=False, error=exc.message)

        next_node = context.config.get("true_path") if result else context.config.get("false_path")
        return ExecutorResult(success=True, output={"result": result, "next_node": next_node})


class TransformExecutor:
    type = "transform"

    def validate_config(self, config: dict[str, Any]) -> None:
        if "mapping_rules" not in config:
            raise AppError(
                "Missing 'mapping_rules' in transform executor config",
                code="invalid_executor_config",
            )

    async def execute(self, context: ExecutionContext) -> ExecutorResult:
        data = {"input": context.workflow_input, "upstream": context.upstream_outputs}
        mapping_rules = context.config.get("mapping_rules", {})
        output: dict[str, Any] = {}
        for key, rule in mapping_rules.items():
            if not isinstance(rule, dict):
                output[key] = rule
            elif "value" in rule:
                output[key] = rule["value"]
            elif "source" in rule:
                output[key] = _resolve_path(data, rule["source"])
        return ExecutorResult(success=True, output=output)


class WebhookExecutor:
    type = "webhook"

    def validate_config(self, config: dict[str, Any]) -> None:
        if "target_url" not in config:
            raise AppError(
                "Missing 'target_url' in webhook executor config",
                code="invalid_executor_config",
            )
        target_url = config["target_url"]
        if not isinstance(target_url, str) or not target_url.startswith(("http://", "https://")):
            raise AppError(
                "Invalid 'target_url' in webhook executor config",
                code="invalid_executor_config",
            )

    async def execute(self, context: ExecutionContext) -> ExecutorResult:
        config = context.config
        timeout = config.get("timeout_seconds", 10)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    config["target_url"],
                    headers=config.get("headers") or {},
                    json=config.get("payload_template"),
                )
        except httpx.HTTPError as exc:
            logger.warning("webhook executor request failed for node %s", context.node_id)
            return ExecutorResult(success=False, error=str(exc))

        if response.status_code >= 400:
            return ExecutorResult(
                success=False, error=f"HTTP {response.status_code}: {response.text[:200]}"
            )
        return ExecutorResult(success=True, output={"status_code": response.status_code})


class NotificationExecutor:
    type = "notification"

    def validate_config(self, config: dict[str, Any]) -> None:
        if "message" not in config:
            raise AppError(
                "Missing 'message' in notification executor config",
                code="invalid_executor_config",
            )

    async def execute(self, context: ExecutionContext) -> ExecutorResult:
        logger.info("notification for node %s: %s", context.node_id, context.config.get("message"))
        return ExecutorResult(success=True, output={"notified": True})


class ExecutorRegistry:
    def __init__(self) -> None:
        self._executors: dict[str, Executor] = {}

    def register(self, executor: Executor) -> None:
        self._executors[executor.type] = executor

    def get(self, executor_type: str) -> Executor:
        executor = self._executors.get(executor_type)
        if not executor:
            raise AppError(f"Unknown executor type: {executor_type}", code="unknown_executor_type")
        return executor


_default_registry = ExecutorRegistry()
_default_registry.register(HttpExecutor())
_default_registry.register(DelayExecutor())
_default_registry.register(ConditionExecutor())
_default_registry.register(TransformExecutor())
_default_registry.register(WebhookExecutor())
_default_registry.register(NotificationExecutor())


def get_executor_registry() -> ExecutorRegistry:
    return _default_registry
