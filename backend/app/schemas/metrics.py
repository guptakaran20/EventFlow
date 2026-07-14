from pydantic import BaseModel


class MetricsSummaryResponse(BaseModel):
    active_executions: int
    queued_nodes: int
    running_nodes: int
    workers: int
    active_workers: int
    queue_depth: int
    dead_letter_jobs: int
