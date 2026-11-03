"""Wires every repository to one shared AsyncSession — used by UnitOfWork
so a service can touch multiple aggregates within a single transaction."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from memory_platform.repositories.document_repository import DocumentChunkRepository, DocumentRepository
from memory_platform.repositories.embedding_record_repository import EmbeddingRecordRepository
from memory_platform.repositories.governance_repository import (
    AuditLogEntryRepository,
    PermissionGrantRepository,
    RetentionPolicyRepository,
)
from memory_platform.repositories.knowledge_graph_repository import KGEntityRepository, KGRelationshipRepository
from memory_platform.repositories.knowledge_repository import (
    KnowledgeBaseRepository,
    KnowledgeCollectionRepository,
    KnowledgeItemRepository,
    KnowledgeItemVersionRepository,
)
from memory_platform.repositories.memory_entry_repository import MemoryEntryRepository
from memory_platform.repositories.memory_type_policy_repository import MemoryTypePolicyRepository
from memory_platform.repositories.observability_repository import ContextAssemblyLogRepository, RetrievalLogRepository
from memory_platform.repositories.workspace_repository import WorkspaceRepository


class RepositoryRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.workspaces = WorkspaceRepository(session)
        self.memory_type_policies = MemoryTypePolicyRepository(session)
        self.memory_entries = MemoryEntryRepository(session)
        self.knowledge_bases = KnowledgeBaseRepository(session)
        self.knowledge_collections = KnowledgeCollectionRepository(session)
        self.knowledge_items = KnowledgeItemRepository(session)
        self.knowledge_item_versions = KnowledgeItemVersionRepository(session)
        self.documents = DocumentRepository(session)
        self.document_chunks = DocumentChunkRepository(session)
        self.embedding_records = EmbeddingRecordRepository(session)
        self.kg_entities = KGEntityRepository(session)
        self.kg_relationships = KGRelationshipRepository(session)
        self.retrieval_logs = RetrievalLogRepository(session)
        self.context_assembly_logs = ContextAssemblyLogRepository(session)
        self.permission_grants = PermissionGrantRepository(session)
        self.retention_policies = RetentionPolicyRepository(session)
        self.audit_log = AuditLogEntryRepository(session)
