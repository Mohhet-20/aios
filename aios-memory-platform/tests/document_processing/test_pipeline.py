import json

import pytest

from memory_platform.document_processing.pipeline import DocumentProcessingService
from memory_platform.domain.enums import DocumentStatus, DocumentType
from memory_platform.models.workspace import WorkspaceModel


async def _workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))


@pytest.mark.asyncio
async def test_process_markdown_document_end_to_end_without_ai_core(repos):
    await _workspace(repos)
    svc = DocumentProcessingService(repos)
    doc = await svc.upload_document(workspace_id="ws-1", title="Notes", document_type=DocumentType.MARKDOWN, uploaded_by="user-1", filename="notes.md")
    assert doc.status == DocumentStatus.PENDING.value

    raw = b"# Notes\n\nThis is the first paragraph.\n\nThis is the second paragraph with more detail."
    processed = await svc.process_document(doc.id, raw, classify=False, generate_embeddings=False)
    assert processed.status == DocumentStatus.PROCESSED.value
    assert processed.extracted_text_length > 0
    assert processed.processed_at is not None
    assert processed.lineage["processing_history"][0]["step"] == "uploaded"
    assert any(h["step"] == "extracted" for h in processed.lineage["processing_history"])

    chunks = await svc.list_chunks(doc.id)
    assert len(chunks) >= 1
    assert chunks[0].token_count > 0


@pytest.mark.asyncio
async def test_process_document_with_classification_and_embeddings(repos, scripted_ai_core):
    from ai_core.schemas.enums import FinishReason
    from ai_core.schemas.responses import ExecutionMetadata, GenerationResponse
    from ai_core.schemas.usage import TokenUsage

    ai_core, provider = scripted_ai_core
    await _workspace(repos)
    svc = DocumentProcessingService(repos, ai_core=ai_core)
    doc = await svc.upload_document(workspace_id="ws-1", title="Report", document_type=DocumentType.TEXT, uploaded_by="user-1")

    payload = {"categories": ["engineering"], "topics": ["testing"], "language": "en", "confidence": 0.8}
    provider.push(GenerationResponse(
        content=json.dumps(payload), finish_reason=FinishReason.STOP, usage=TokenUsage(input_tokens=5, output_tokens=5),
        execution=ExecutionMetadata(request_id="r", provider="test", model="m1", latency_ms=1.0),
    ))

    processed = await svc.process_document(doc.id, b"A short report about our testing strategy.")
    assert processed.classification["categories"] == ["engineering"]
    assert processed.language == "en"

    chunks = await svc.list_chunks(doc.id)
    assert all(c.embedding_id is not None for c in chunks)
    record = await repos.embedding_records.get_or_404(chunks[0].embedding_id)
    assert record.source_type == "document_chunk"
    assert record.dimensions == 8  # scripted embed() fallback produces dim-8 vectors


@pytest.mark.asyncio
async def test_process_document_failure_marks_status_failed(repos):
    await _workspace(repos)
    svc = DocumentProcessingService(repos)
    doc = await svc.upload_document(workspace_id="ws-1", title="Bad PDF", document_type=DocumentType.PDF, uploaded_by="user-1")
    from memory_platform.core.exceptions import DocumentProcessingError
    with pytest.raises(DocumentProcessingError):
        await svc.process_document(doc.id, b"not a real pdf at all")
    reloaded = await svc.get_document(doc.id)
    assert reloaded.status == DocumentStatus.FAILED.value
    assert reloaded.error_message is not None
