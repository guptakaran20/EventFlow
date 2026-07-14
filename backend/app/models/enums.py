import enum


class ExecutionStatus(enum.StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL_FAILED = "PARTIAL_FAILED"
    CANCELLED = "CANCELLED"


class NodeExecutionStatus(enum.StrEnum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    SKIPPED = "SKIPPED"
    DEAD_LETTERED = "DEAD_LETTERED"


class WorkerStatus(enum.StrEnum):
    STARTING = "STARTING"
    IDLE = "IDLE"
    BUSY = "BUSY"
    STOPPING = "STOPPING"
    OFFLINE = "OFFLINE"


class LogLevel(enum.StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
