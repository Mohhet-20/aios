"""Dependency-injection providers for every business service.

Each `get_*_service` function is a FastAPI dependency: it takes a per-request
`AsyncSession` (via `get_db_session`) and any process-wide singletons
(event bus, worker pool, AI provider, vector store, plugin registry),
constructs the concrete repository/service graph, and hands the service to
the router. Routers never construct a service or repository themselves —
this file is the single place that wiring happens, which is what makes it
possible to change a service's dependencies without touching every router
that uses it.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.events.bus import EventBus, event_bus
from app.infrastructure.ai_providers.base import ModelProviderAdapter
from app.infrastructure.ai_providers.stub_provider import stub_provider
from app.infrastructure.vector_store.base import VectorStore
from app.infrastructure.vector_store.in_memory_vector_store import in_memory_vector_store
from app.plugins.registry import PluginRegistry, plugin_registry
from app.repositories.agent_repository import AgentRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.configuration_repository import ConfigurationRepository
from app.repositories.conversation_repository import ConversationMessageRepository, ConversationRepository
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.experiment_repository import ExperimentRepository
from app.repositories.knowledge_repository import DocumentRepository, KnowledgeCollectionRepository
from app.repositories.memory_repository import MemoryRepository
from app.repositories.model_repository import ModelRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.organization_repository import (
    OrganizationMembershipRepository,
    OrganizationRepository,
    TeamMembershipRepository,
    TeamRepository,
)
from app.repositories.plugin_repository import PluginRepository, ToolRepository
from app.repositories.prompt_repository import PromptRepository, PromptVersionRepository
from app.repositories.session_repository import ApiKeyRepository, RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workflow_repository import WorkflowExecutionRepository, WorkflowRepository
from app.repositories.workspace_repository import ProjectRepository, WorkspaceRepository
from app.services.agent_service import AgentService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.configuration_service import ConfigurationService
from app.services.conversation_service import ConversationService
from app.services.dataset_service import DatasetService
from app.services.embedding_service import EmbeddingService
from app.services.evaluation_service import EvaluationService
from app.services.experiment_service import ExperimentService
from app.services.inference_service import InferenceService
from app.services.knowledge_service import DocumentService, KnowledgeService
from app.services.memory_service import MemoryService
from app.services.model_service import ModelService
from app.services.monitoring_service import MonitoringService
from app.services.notification_service import NotificationService
from app.services.organization_service import OrganizationService, TeamService
from app.services.plugin_service import PluginService
from app.services.prompt_service import PromptService
from app.services.search_service import SearchService
from app.services.user_service import UserService
from app.services.vector_service import VectorService
from app.services.workflow_service import WorkflowService
from app.services.workspace_service import ProjectService, WorkspaceService
from app.workers.in_process_worker import InProcessWorkerPool, worker_pool


def get_event_bus() -> EventBus:
    return event_bus


def get_task_queue() -> InProcessWorkerPool:
    return worker_pool


def get_ai_provider() -> ModelProviderAdapter:
    return stub_provider


def get_vector_store() -> VectorStore:
    return in_memory_vector_store


def get_plugin_registry() -> PluginRegistry:
    return plugin_registry


def get_auth_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> AuthService:
    return AuthService(UserRepository(session), RefreshTokenRepository(session), event_bus)


def get_user_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> UserService:
    return UserService(UserRepository(session))


def get_organization_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> OrganizationService:
    return OrganizationService(OrganizationRepository(session), OrganizationMembershipRepository(session))


def get_team_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> TeamService:
    return TeamService(TeamRepository(session), TeamMembershipRepository(session))


def get_workspace_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> WorkspaceService:
    return WorkspaceService(WorkspaceRepository(session))


def get_project_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> ProjectService:
    return ProjectService(ProjectRepository(session))


def get_agent_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> AgentService:
    return AgentService(AgentRepository(session))


def get_prompt_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> PromptService:
    return PromptService(PromptRepository(session), PromptVersionRepository(session), event_bus)


def get_model_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> ModelService:
    return ModelService(ModelRepository(session))


def get_workflow_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> WorkflowService:
    return WorkflowService(
        WorkflowRepository(session), WorkflowExecutionRepository(session), event_bus, worker_pool
    )


def get_inference_service() -> InferenceService:
    return InferenceService(stub_provider, event_bus)


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(stub_provider)


def get_vector_service() -> VectorService:
    return VectorService(in_memory_vector_store)


def get_memory_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> MemoryService:
    return MemoryService(
        MemoryRepository(session), EmbeddingService(stub_provider), VectorService(in_memory_vector_store)
    )


def get_evaluation_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> EvaluationService:
    return EvaluationService(EvaluationRepository(session), event_bus, worker_pool)


def get_knowledge_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> KnowledgeService:
    return KnowledgeService(KnowledgeCollectionRepository(session))


def get_document_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> DocumentService:
    return DocumentService(DocumentRepository(session), KnowledgeCollectionRepository(session), worker_pool)


def get_dataset_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> DatasetService:
    return DatasetService(DatasetRepository(session))


def get_experiment_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> ExperimentService:
    return ExperimentService(ExperimentRepository(session))


def get_conversation_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> ConversationService:
    return ConversationService(ConversationRepository(session), ConversationMessageRepository(session))


def get_search_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> SearchService:
    return SearchService(PromptRepository(session), AgentRepository(session), DocumentRepository(session))


def get_monitoring_service() -> MonitoringService:
    return MonitoringService(worker_pool)


def get_notification_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> NotificationService:
    return NotificationService(NotificationRepository(session), event_bus)


def get_configuration_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> ConfigurationService:
    return ConfigurationService(ConfigurationRepository(session))


def get_plugin_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> PluginService:
    return PluginService(PluginRepository(session), ToolRepository(session), plugin_registry)


def get_audit_service(session: AsyncSession = Depends(get_db_session, scope="function")) -> AuditService:
    return AuditService(AuditRepository(session))


def get_api_key_repository(session: AsyncSession = Depends(get_db_session, scope="function")) -> ApiKeyRepository:
    return ApiKeyRepository(session)
