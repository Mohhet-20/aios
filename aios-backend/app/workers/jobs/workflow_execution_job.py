"""Long-running workflow execution job.

Actually driving a multi-step workflow to completion (invoking agents,
calling tools, evaluating branch conditions) is Workflow Engine business
logic that depends on the AI Core being real — out of scope per this
prompt's scope boundary ("do NOT implement AI model logic yet"). This job
defines the *shape* the real implementation will fill in: given an
execution ID, walk `WorkflowModel.definition["nodes"]` in topological order
and update `WorkflowExecutionModel.steps` as each step resolves.
"""

from app.logging.setup import get_logger

logger = get_logger(__name__)


async def run_workflow_execution(execution_id: str) -> dict:
    logger.info("workflow_execution_job_started", execution_id=execution_id)
    # Intentionally stubbed. Real multi-step workflow execution (agent
    # invocation, tool calls, branch evaluation) now lives in the sibling
    # `aios-workflow-engine` and `aios-agent-platform` services — wiring
    # this job to delegate to them is a deliberate future integration,
    # not an oversight.
    return {"execution_id": execution_id, "status": "completed", "note": "stubbed — no AI logic yet"}
