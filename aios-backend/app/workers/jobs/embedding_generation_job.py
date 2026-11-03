"""Generates embeddings for newly-ingested documents/memory items. Delegates
to `EmbeddingService`, which delegates the actual vector generation to the
stubbed AI provider adapter."""

from app.logging.setup import get_logger

logger = get_logger(__name__)


async def run_embedding_generation(document_id: str) -> dict:
    logger.info("embedding_generation_job_started", document_id=document_id)
    # Intentionally stubbed: this repo's AI provider adapter is a
    # placeholder. Real embedding generation now lives in the sibling
    # `aios-ai-core` service's Embedding Engine — wiring this job to call
    # it over HTTP is a deliberate future integration, not an oversight.
    return {"document_id": document_id, "note": "stubbed — no AI logic yet"}
