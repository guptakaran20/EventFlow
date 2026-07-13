import re
from typing import Any, Protocol

from app.core.errors import AppError


class Executor(Protocol):
    type: str

    def validate_config(self, config: dict[str, Any]) -> None: ...


class HttpExecutor:
    type = "http"

    def validate_config(self, config: dict[str, Any]) -> None:
        if "url" not in config:
            raise AppError("Missing 'url' in http executor config", code="invalid_executor_config")
        if not isinstance(config["url"], str) or not config["url"].startswith(
            ("http://", "https://")
        ):
            raise AppError("Invalid 'url' in http executor config", code="invalid_executor_config")


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


class ConditionExecutor:
    type = "condition"

    def validate_config(self, config: dict[str, Any]) -> None:
        for field in ["expression", "true_path", "false_path"]:
            if field not in config:
                raise AppError(
                    f"Missing '{field}' in condition executor config",
                    code="invalid_executor_config",
                )

        # Simple safeguard to prevent eval-like expressions
        expr = config["expression"]
        if not isinstance(expr, str):
            raise AppError("'expression' must be a string", code="invalid_executor_config")

        # Check for disallowed words typically used in exploits (just a stub validation for now)
        if re.search(r"(import|exec|eval|os|sys|open)", expr):
            raise AppError("Unsafe expression detected", code="invalid_executor_config")


class TransformExecutor:
    type = "transform"

    def validate_config(self, config: dict[str, Any]) -> None:
        if "mapping_rules" not in config:
            raise AppError(
                "Missing 'mapping_rules' in transform executor config",
                code="invalid_executor_config",
            )


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


class NotificationExecutor:
    type = "notification"

    def validate_config(self, config: dict[str, Any]) -> None:
        if "message" not in config:
            raise AppError(
                "Missing 'message' in notification executor config",
                code="invalid_executor_config",
            )


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
