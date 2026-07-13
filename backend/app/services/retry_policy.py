from app.schemas.workflow import Node, RetryPolicy, WorkflowDefinition

DEFAULT_RETRY_POLICY = RetryPolicy()


def resolve_retry_policy(node: Node, definition: WorkflowDefinition) -> RetryPolicy:
    """Resolve retry policy: node override > workflow default > safe default."""
    if node.retry_policy is not None:
        return node.retry_policy
    if definition.default_retry_policy is not None:
        return definition.default_retry_policy
    return DEFAULT_RETRY_POLICY
