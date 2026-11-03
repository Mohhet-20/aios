"""KnowledgeService and DocumentService together back the Knowledge
Base / Document Management pages: collections group documents, and adding a
document bumps its collection's `document_count` denormalized counter (kept
in sync here rather than computed with a COUNT query on every read, since
the collection list page reads this far more often than documents change).
"""

from __future__ import annotations

from app.application.services.base_service import BaseCRUDService
from app.models.knowledge import DocumentModel, KnowledgeCollectionModel
from app.repositories.knowledge_repository import DocumentRepository, KnowledgeCollectionRepository
from app.workers.jobs.document_processing_job import process_document
from app.workers.task_queue import TaskQueue


class KnowledgeService(BaseCRUDService[KnowledgeCollectionModel]):
    def __init__(self, repository: KnowledgeCollectionRepository):
        super().__init__(repository)


class DocumentService(BaseCRUDService[DocumentModel]):
    def __init__(
        self,
        repository: DocumentRepository,
        collections: KnowledgeCollectionRepository,
        task_queue: TaskQueue,
    ):
        super().__init__(repository)
        self.collections = collections
        self.task_queue = task_queue

    async def upload(
        self, workspace_id: str, name: str, size_bytes: int, collection_id: str | None
    ) -> DocumentModel:
        doc = DocumentModel(
            workspace_id=workspace_id,
            collection_id=collection_id,
            name=name,
            size_bytes=size_bytes,
            status="pending",
        )
        doc = await self.repository.add(doc)

        if collection_id:
            collection = await self.collections.get(collection_id)
            if collection:
                collection.document_count += 1
                await self.collections.update(collection)

        await self.task_queue.enqueue(f"document_processing:{doc.id}", process_document, doc.id)
        return doc
