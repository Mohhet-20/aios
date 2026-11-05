"""Document ingestion pipeline: chunk -> embed -> index. Chunking/parsing
logic (PDF/DOCX/HTML extraction) is infrastructure work independent of AI
model logic and could be implemented today; it's left as a stub alongside
the embedding step for now so the whole pipeline lands together in
one later pass rather than half now, half later."""

from app.logging.setup import get_logger

logger = get_logger(__name__)


async def process_document(document_id: str) -> dict:
    logger.info("document_processing_job_started", document_id=document_id)
    # Intentionally stubbed. Real chunking/embedding/indexing now lives in
    # the sibling `aios-memory-platform` service's Document Intelligence and
    # Vector Platform modules — wiring this job to delegate to it is a
    # deliberate future integration, not an oversight.
    return {"document_id": document_id, "note": "stubbed — chunking/embedding pending AI Core"}
