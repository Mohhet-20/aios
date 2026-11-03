"""Batch inference job: fan out a prompt across many inputs (e.g. re-run an
eval dataset through a new model). Delegates to `InferenceService`, which
itself delegates the actual generation call to the stubbed AI provider
adapter (`app.infrastructure.ai_providers`) — see that module for why."""

from app.logging.setup import get_logger

logger = get_logger(__name__)


async def run_batch_inference(model_id: str, inputs: list[str]) -> dict:
    logger.info("batch_inference_job_started", model_id=model_id, input_count=len(inputs))
    # Intentionally stubbed: this repo's `app.infrastructure.ai_providers`
    # adapter is a placeholder. Real generation now lives in the sibling
    # `aios-ai-core` service (a separate deployable in this system, not a
    # module of this repo) — wiring this job to call it over HTTP is a
    # deliberate future integration, not an oversight.
    return {"model_id": model_id, "processed": len(inputs), "note": "stubbed — no AI logic yet"}
