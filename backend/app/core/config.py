from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class TransportMode(StrEnum):
    LOCAL = "local"
    GRPC = "grpc"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "EventFlow"
    environment: str = "development"
    debug: bool = False

    # Internal transport: switches API/worker engine calls between direct
    # in-process calls and gRPC-backed calls without changing business logic.
    eventflow_internal_transport: TransportMode = TransportMode.LOCAL

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://eventflow:eventflow@localhost:5432/eventflow"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_stream_name: str = "eventflow:jobs"
    redis_consumer_group: str = "eventflow-workers"
    # "memory" (default, no Redis required) or "redis" (RedisStreamQueuePublisher)
    queue_publisher_backend: str = "memory"

    # Worker lifecycle
    worker_name: str | None = None
    worker_concurrency: int = 4
    worker_heartbeat_interval_seconds: float = 5.0
    worker_pending_idle_timeout_seconds: float = 600.0
    worker_recovery_poll_interval_seconds: float = 30.0

    # WebSocket heartbeat: server ping interval to detect dead client sockets.
    websocket_heartbeat_interval_seconds: float = 20.0

    # API key auth
    api_key_header_name: str = "X-EventFlow-API-Key"
    # Comma-separated bootstrap API keys usable before the API key table/service
    # is implemented in a later phase. Not for production use.
    bootstrap_api_keys: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def bootstrap_api_keys_list(self) -> list[str]:
        return [key.strip() for key in self.bootstrap_api_keys.split(",") if key.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
