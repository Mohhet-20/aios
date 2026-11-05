"""FastAPI dependency wiring: DB session -> RepositoryRegistry -> every
service, plus AI Core and a minimal caller-identity dependency.

Auth is intentionally minimal here — this platform expects to sit behind
an already-authenticated gateway (e.g. the AIOS backend from Phase 3,
which owns full JWT/session auth) that forwards the caller's identity
via the `X-User-Id` header, the same seam every prior AIOS platform in
this series uses. Every router depends on `get_current_actor_id`, never
on the header directly, so swapping in real token validation later is a
one-file change.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from ai_core.bootstrap import AICoreContext
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from memory_platform.analytics.analytics_service import AnalyticsService
from memory_platform.config.settings import Settings, get_settings
from memory_platform.context_engine.context_assembly_service import ContextAssemblyService
from memory_platform.conversation_memory.conversation_memory_service import ConversationMemoryService
from memory_platform.database.session import get_db_session
from memory_platform.dependencies.ai_core_provider import get_default_ai_core_context
from memory_platform.document_processing.pipeline import DocumentProcessingService
from memory_platform.episodic_memory.episodic_memory_service import EpisodicMemoryService
from memory_platform.governance.access_policy_service import AccessPolicyService
from memory_platform.governance.audit_service import AuditService
from memory_platform.governance.rbac_service import RBACService
from memory_platform.governance.retention_policy_service import RetentionPolicyService
from memory_platform.knowledge.knowledge_service import KnowledgeService
from memory_platform.knowledge_graph.graph_service import KnowledgeGraphService
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.memory_core.working_memory_service import WorkingMemoryService
from memory_platform.repositories.registry import RepositoryRegistry
from memory_platform.retrieval.retrieval_service import RetrievalService
from memory_platform.security.encryption_service import EncryptionService
from memory_platform.vector_store.vector_platform_service import VectorPlatformService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session, scope="function")) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_ai_core() -> AICoreContext:
    return get_default_ai_core_context()


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id


# -- memory core -----------------------------------------------------------------------

def get_memory_service(repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core)) -> MemoryService:
    return MemoryService(repos, ai_core=ai_core)


def get_conversation_memory_service(
    repos: RepositoryRegistry = Depends(get_repos), memory: MemoryService = Depends(get_memory_service), ai_core: AICoreContext = Depends(get_ai_core),
) -> ConversationMemoryService:
    return ConversationMemoryService(repos, memory, ai_core=ai_core)


def get_episodic_memory_service(repos: RepositoryRegistry = Depends(get_repos), memory: MemoryService = Depends(get_memory_service)) -> EpisodicMemoryService:
    return EpisodicMemoryService(repos, memory)


def get_working_memory_service(repos: RepositoryRegistry = Depends(get_repos), memory: MemoryService = Depends(get_memory_service)) -> WorkingMemoryService:
    return WorkingMemoryService(repos, memory)


# -- knowledge / documents / vectors ----------------------------------------------------

def get_knowledge_service(repos: RepositoryRegistry = Depends(get_repos)) -> KnowledgeService:
    return KnowledgeService(repos)


def get_document_processing_service(repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core)) -> DocumentProcessingService:
    return DocumentProcessingService(repos, ai_core=ai_core)


def get_vector_platform_service(repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core)) -> VectorPlatformService:
    return VectorPlatformService(repos, ai_core)


def get_knowledge_graph_service(repos: RepositoryRegistry = Depends(get_repos)) -> KnowledgeGraphService:
    return KnowledgeGraphService(repos)


# -- retrieval / context -----------------------------------------------------------------

def get_retrieval_service(
    repos: RepositoryRegistry = Depends(get_repos), vector_platform: VectorPlatformService = Depends(get_vector_platform_service), ai_core: AICoreContext = Depends(get_ai_core),
) -> RetrievalService:
    return RetrievalService(repos, vector_platform=vector_platform, ai_core=ai_core)


def get_context_assembly_service(retrieval: RetrievalService = Depends(get_retrieval_service), ai_core: AICoreContext = Depends(get_ai_core)) -> ContextAssemblyService:
    return ContextAssemblyService(retrieval, ai_core=ai_core)


# -- governance / security ---------------------------------------------------------------

def get_rbac_service(repos: RepositoryRegistry = Depends(get_repos)) -> RBACService:
    return RBACService(repos)


def get_access_policy_service(rbac: RBACService = Depends(get_rbac_service)) -> AccessPolicyService:
    return AccessPolicyService(rbac)


def get_retention_policy_service(repos: RepositoryRegistry = Depends(get_repos), memory: MemoryService = Depends(get_memory_service)) -> RetentionPolicyService:
    return RetentionPolicyService(repos, memory)


def get_audit_service(repos: RepositoryRegistry = Depends(get_repos)) -> AuditService:
    return AuditService(repos)


def get_encryption_service(settings: Settings = Depends(get_settings_dep)) -> EncryptionService:
    return EncryptionService(settings)


# -- observability -----------------------------------------------------------------------

def get_analytics_service(repos: RepositoryRegistry = Depends(get_repos)) -> AnalyticsService:
    return AnalyticsService(repos)
