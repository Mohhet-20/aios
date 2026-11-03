"""NodeTypeRegistry: the data-driven catalog of all ~30 node types the
Execution Engine can dispatch to. Each entry seeds one `NodeDefinitionModel`
row — policy/metadata only. The actual handler logic for a node type lives
in `workflow_engine/handlers/` (see Task 87); adding a 31st *policy*
variant of an existing handler (e.g. a new REST_API preset) is a row
insert here, not a new Python class."""
from __future__ import annotations

from dataclasses import dataclass, field

from workflow_platform.domain.enums import NodeType


@dataclass(frozen=True)
class NodeTypeSpec:
    key: str
    name: str
    description: str
    category: str
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    default_config: dict = field(default_factory=dict)
    default_timeout_seconds: int = 300
    default_max_retries: int = 0
    default_retry_backoff_seconds: float = 2.0
    is_compensable: bool = False


# category buckets: control_flow | ai | integration | human | data | custom
NODE_TYPE_SPECS: list[NodeTypeSpec] = [
    NodeTypeSpec(NodeType.START.value, "Start", "Entry point of a workflow graph; exactly one per version.", "control_flow"),
    NodeTypeSpec(NodeType.END.value, "End", "Terminal node; a graph may have several.", "control_flow"),
    NodeTypeSpec(NodeType.AGENT.value, "Agent", "Invokes an AI Agent via the Agent Platform bridge.", "ai",
                 input_schema={"agent_id": "string", "task": "string"}, default_timeout_seconds=600, default_max_retries=2),
    NodeTypeSpec(NodeType.PROMPT.value, "Prompt", "Executes a versioned prompt via the Prompt Platform bridge.", "ai",
                 input_schema={"prompt_id": "string", "variables": "object"}, default_max_retries=2),
    NodeTypeSpec(NodeType.MEMORY_READ.value, "Memory Read", "Reads from the Memory Platform via the memory bridge.", "ai",
                 input_schema={"scope": "string", "query": "object"}),
    NodeTypeSpec(NodeType.MEMORY_WRITE.value, "Memory Write", "Writes to the Memory Platform via the memory bridge.", "ai",
                 input_schema={"scope": "string", "content": "object"}, is_compensable=True),
    NodeTypeSpec(NodeType.RETRIEVER.value, "Retriever", "Runs hybrid retrieval via the Memory Platform bridge.", "ai",
                 input_schema={"query": "string", "top_k": "integer"}),
    NodeTypeSpec(NodeType.KNOWLEDGE_SEARCH.value, "Knowledge Search", "Searches the Knowledge Platform via the memory bridge.", "ai",
                 input_schema={"query": "string"}),
    NodeTypeSpec(NodeType.DECISION.value, "Decision", "Multi-way branch based on an expression evaluated against context.", "control_flow"),
    NodeTypeSpec(NodeType.CONDITION.value, "Condition", "Boolean gate; routes to one of two outgoing edges.", "control_flow"),
    NodeTypeSpec(NodeType.LOOP.value, "Loop", "Repeats a sub-graph while a condition holds or over a collection; the one node type allowed to form a cycle.", "control_flow",
                 default_config={"max_iterations": 1000}),
    NodeTypeSpec(NodeType.PARALLEL_BRANCH.value, "Parallel Branch", "Fans execution out across multiple outgoing edges concurrently.", "control_flow"),
    NodeTypeSpec(NodeType.MERGE.value, "Merge", "Joins parallel branches back into a single execution path.", "control_flow",
                 default_config={"wait_for": "all"}),
    NodeTypeSpec(NodeType.DELAY.value, "Delay", "Pauses execution for a fixed duration.", "control_flow",
                 input_schema={"seconds": "number"}),
    NodeTypeSpec(NodeType.WAIT.value, "Wait", "Pauses execution until an external event or condition is satisfied.", "control_flow",
                 default_timeout_seconds=86400),
    NodeTypeSpec(NodeType.APPROVAL.value, "Approval", "Pauses execution for human-in-the-loop approval.", "human",
                 input_schema={"approval_chain": "array", "reason": "string"}, default_timeout_seconds=259200),
    NodeTypeSpec(NodeType.NOTIFICATION.value, "Notification", "Publishes a notification event/webhook.", "human"),
    NodeTypeSpec(NodeType.WEBHOOK.value, "Webhook", "Registers or fires an outbound webhook delivery.", "integration", default_max_retries=3),
    NodeTypeSpec(NodeType.REST_API.value, "REST API", "Calls an external HTTP API.", "integration",
                 input_schema={"method": "string", "url": "string"}, default_max_retries=3, is_compensable=True),
    NodeTypeSpec(NodeType.DATABASE_QUERY.value, "Database Query", "Executes a parameterized database query.", "data", default_max_retries=1),
    NodeTypeSpec(NodeType.PYTHON_EXECUTION.value, "Python Execution", "Runs a sandboxed Python function against context variables.", "data"),
    NodeTypeSpec(NodeType.FILE_UPLOAD.value, "File Upload", "Accepts a file into the execution context.", "data"),
    NodeTypeSpec(NodeType.FILE_PROCESSING.value, "File Processing", "Transforms/validates a file already in context.", "data"),
    NodeTypeSpec(NodeType.DOCUMENT_PARSER.value, "Document Parser", "Delegates to the Memory Platform's Document Intelligence bridge.", "ai", default_timeout_seconds=600),
    NodeTypeSpec(NodeType.EMBEDDING_GENERATOR.value, "Embedding Generator", "Generates embeddings via AI Core's embedding engine.", "ai"),
    NodeTypeSpec(NodeType.LLM_CALL.value, "LLM Call", "Direct LLM generation call via AI Core's execution engine.", "ai", default_max_retries=2),
    NodeTypeSpec(NodeType.FUNCTION_CALL.value, "Function Call", "Invokes a registered tool/function via the tool bridge.", "integration", default_max_retries=1),
    NodeTypeSpec(NodeType.ERROR_HANDLER.value, "Error Handler", "Catches a failure from a preceding node and routes to recovery logic.", "control_flow"),
    NodeTypeSpec(NodeType.RETRY.value, "Retry", "Explicitly re-invokes a prior node with backoff, outside the automatic retry policy.", "control_flow"),
    NodeTypeSpec(NodeType.CUSTOM.value, "Custom", "Escape hatch for a workspace-registered custom handler.", "custom"),
]

NODE_TYPE_SPECS_BY_KEY: dict[str, NodeTypeSpec] = {spec.key: spec for spec in NODE_TYPE_SPECS}

# Node types allowed to participate in a graph cycle (Loop is the sanctioned
# looping construct; everything else forming a cycle is a workflow-authoring bug).
CYCLE_TOLERANT_NODE_TYPES = {NodeType.LOOP.value}


async def seed_node_definitions(repos) -> int:
    """Idempotently seeds every built-in node type as a `NodeDefinitionModel`
    row. Returns the number of newly-inserted rows."""
    from workflow_platform.models.node_definition import NodeDefinitionModel

    inserted = 0
    for spec in NODE_TYPE_SPECS:
        existing = await repos.node_definitions.get_by_key(spec.key)
        if existing is not None:
            continue
        await repos.node_definitions.add(NodeDefinitionModel(
            key=spec.key, name=spec.name, description=spec.description, category=spec.category,
            input_schema=spec.input_schema, output_schema=spec.output_schema, default_config=spec.default_config,
            default_timeout_seconds=spec.default_timeout_seconds, default_max_retries=spec.default_max_retries,
            default_retry_backoff_seconds=spec.default_retry_backoff_seconds, is_compensable=spec.is_compensable,
            is_builtin=True,
        ))
        inserted += 1
    return inserted
