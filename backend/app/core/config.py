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

    # API key auth
    api_key_header_name: str = "X-EventFlow-API-Key"
    # Comma-separated bootstrap API keys usable before the API key table/service
    # is implemented in a later phase. Not for production use.
    bootstrap_api_keys: str = ""

    @property
    def bootstrap_api_keys_list(self) -> list[str]:
        return [key.strip() for key in self.bootstrap_api_keys.split(",") if key.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
