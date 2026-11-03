"""Runs an evaluation suite against a dataset. The grading step (exact
match / semantic similarity / LLM-as-judge) requires the AI Core, so this
job is wired for the orchestration (fetch dataset, iterate examples, persist
an `EvaluationRunModel`) with the actual grading call left as the seam for
the AI Core prompt."""

from app.logging.setup import get_logger

logger = get_logger(__name__)


async def run_evaluation(evaluation_run_id: str) -> dict:
    logger.info("evaluation_job_started", evaluation_run_id=evaluation_run_id)
    # Intentionally stubbed. Real grading (exact match / semantic similarity
    # / LLM-as-judge) now lives in the sibling `aios-evaluation-platform`
    # service's Quality Metrics Engine — wiring this job to delegate to it
    # is a deliberate future integration, not an oversight.
    return {"evaluation_run_id": evaluation_run_id, "note": "stubbed — no AI logic yet"}
