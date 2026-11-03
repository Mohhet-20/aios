"""Wires every concrete repository to a single `AsyncSession`. `UnitOfWork`
constructs exactly one `RepositoryRegistry` per transaction, so
`uow.repos.prompts`, `uow.repos.workflows`, etc. all share the same session
and therefore the same transaction boundary.
"""

from sqlalchemy.ext.asyncio import AsyncSession

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


class RepositoryRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.organizations = OrganizationRepository(session)
        self.organization_memberships = OrganizationMembershipRepository(session)
        self.teams = TeamRepository(session)
        self.team_memberships = TeamMembershipRepository(session)
        self.workspaces = WorkspaceRepository(session)
        self.projects = ProjectRepository(session)
        self.agents = AgentRepository(session)
        self.prompts = PromptRepository(session)
        self.prompt_versions = PromptVersionRepository(session)
        self.workflows = WorkflowRepository(session)
        self.workflow_executions = WorkflowExecutionRepository(session)
        self.models = ModelRepository(session)
        self.evaluations = EvaluationRepository(session)
        self.memory = MemoryRepository(session)
        self.knowledge_collections = KnowledgeCollectionRepository(session)
        self.documents = DocumentRepository(session)
        self.datasets = DatasetRepository(session)
        self.experiments = ExperimentRepository(session)
        self.conversations = ConversationRepository(session)
        self.conversation_messages = ConversationMessageRepository(session)
        self.notifications = NotificationRepository(session)
        self.audit_logs = AuditRepository(session)
        self.plugins = PluginRepository(session)
        self.tools = ToolRepository(session)
        self.configuration = ConfigurationRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.api_keys = ApiKeyRepository(session)
