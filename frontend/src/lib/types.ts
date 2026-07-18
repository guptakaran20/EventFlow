export type RetryPolicy = {
  max_attempts: number;
  initial_interval: number;
  max_interval: number;
  backoff_multiplier: number;
};

export type Node = {
  id: string;
  type: string;
  name: string;
  config: Record<string, any>;
  retry_policy?: RetryPolicy;
};

export type Edge = {
  from: string;
  to: string;
  condition?: string;
};

export type WorkflowDefinition = {
  name: string;
  description: string;
  nodes: Node[];
  edges: Edge[];
  default_retry_policy?: RetryPolicy;
};

export type WorkflowListResponse = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  latest_version_number: number;
};

export type WorkflowVersionResponse = {
  id: string;
  workflow_id: string;
  version_number: number;
  checksum: string;
  created_at: string;
  definition?: any;
};

export type WorkflowDetailResponse = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  versions: WorkflowVersionResponse[];
};

export type NodeExecutionResponse = {
  id: string;
  execution_id: string;
  node_id: string;
  node_type: string;
  status: string;
  attempt: number;
  max_attempts: number;
  input_payload: Record<string, any> | null;
  output_payload: Record<string, any> | null;
  error_message: string | null;
};

export type ExecutionResponse = {
  id: string;
  workflow_id: string;
  workflow_version_id: string;
  status: string;
  input_payload: Record<string, any> | null;
  error_message: string | null;
  node_executions: NodeExecutionResponse[];
};

export type ExecutionLogResponse = {
  log_id: string;
  timestamp: string;
  level: string;
  message: string;
  metadata: Record<string, any> | null;
};

export type MetricsSummaryResponse = {
  active_executions: number;
  queued_nodes: number;
  running_nodes: number;
  workers: number;
  active_workers: number;
  queue_depth: number;
  dead_letter_jobs: number;
};

export type DeadLetterJobResponse = {
  id: string;
  execution_id: string;
  node_execution_id: string;
  reason: string;
  attempts: number;
  payload: Record<string, any> | null;
  resolved_at: string | null;
  resolution_note: string | null;
  created_at: string;
};

export type WorkerResponse = {
  worker_id: string;
  hostname: string;
  status: string;
  current_job_id: string | null;
  started_at: string;
  last_heartbeat_at: string | null;
  heartbeat_age_seconds: number | null;
};
