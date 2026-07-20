from collections import defaultdict, deque
from typing_extensions import TypedDict

from app.core.errors import AppError
from app.schemas.workflow import WorkflowDefinition
from app.services.executor_registry import ExecutorRegistry


class ValidationResult(TypedDict):
    valid: bool
    root_nodes: list[str]
    topological_order: list[str]


def validate_workflow(workflow: WorkflowDefinition, registry: ExecutorRegistry) -> ValidationResult:
    """
    Validates a WorkflowDefinition for DAG correctness and executor config.
    Returns a ValidationResult if successful.
    Raises AppError for any validation failure.
    """
    nodes_by_id = {}
    for node in workflow.nodes:
        if node.id in nodes_by_id:
            raise AppError(
                f"Duplicate node ID detected: '{node.id}'",
                code="duplicate_node_id",
            )
        nodes_by_id[node.id] = node

        # Validate executor type and config
        try:
            executor = registry.get(node.type)
        except AppError as e:
            raise AppError(
                f"Unknown executor type '{node.type}' for node '{node.id}'",
                code="unknown_executor_type",
            ) from e

        try:
            executor.validate_config(node.config)
        except AppError as e:
            # Re-raise with node context
            raise AppError(
                f"Invalid config for node '{node.id}': {e.message}",
                code="invalid_executor_config",
            ) from e

    # Build adjacency list and in-degrees
    adj = defaultdict(list)
    in_degree = {node.id: 0 for node in workflow.nodes}

    for edge in workflow.edges:
        if edge.from_node not in nodes_by_id:
            raise AppError(
                f"Edge refers to missing source node: '{edge.from_node}'",
                code="missing_edge_reference",
            )
        if edge.to_node not in nodes_by_id:
            raise AppError(
                f"Edge refers to missing target node: '{edge.to_node}'",
                code="missing_edge_reference",
            )

        adj[edge.from_node].append(edge.to_node)
        in_degree[edge.to_node] += 1

    # Kahn's algorithm for topological sorting and cycle detection
    queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
    root_nodes = list(queue)

    if not root_nodes and workflow.nodes:
        raise AppError(
            "Workflow contains a cycle and has no root nodes.",
            code="cycle_detected",
        )

    topological_order = []

    while queue:
        curr = queue.popleft()
        topological_order.append(curr)
        for neighbor in adj[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(topological_order) != len(workflow.nodes):
        raise AppError(
            "Workflow contains a cycle.",
            code="cycle_detected",
        )

    return {
        "valid": True,
        "root_nodes": root_nodes,
        "topological_order": topological_order,
    }
