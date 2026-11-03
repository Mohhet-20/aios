"""RepositoryRegistry: wires every repository to one shared AsyncSession,
so a single unit-of-work-scoped session backs every repository an
application-service call touches. Same pattern as Memory/Agent/Prompt
Platform's `RepositoryRegistry`."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from workflow_platform.repositories.approval_repository import (
    ApprovalCommentRepository,
    ApprovalRequestRepository,
)
from workflow_platform.repositories.checkpoint_repository import CheckpointRepository
from workflow_platform.repositories.events_repository import (
    EventRepository,
    SubscriptionRepository,
    WebhookDeliveryRepository,
)
from workflow_platform.repositories.execution_repository import (
    ExecutionRepository,
    NodeExecutionRepository,
)
from workflow_platform.repositories.governance_repository import (
    AuditLogEntryRepository,
    PermissionGrantRepository,
)
from workflow_platform.repositories.node_definition_repository import NodeDefinitionRepository
from workflow_platform.repositories.node_repository import (
    WorkflowEdgeRepository,
    WorkflowNodeRepository,
)
from workflow_platform.repositories.observability_repository import ExecutionLogRepository
from workflow_platform.repositories.schedule_repository import ScheduleRepository
from workflow_platform.repositories.template_repository import WorkflowTemplateRepository
from workflow_platform.repositories.variable_repository import VariableRepository
from workflow_platform.repositories.workflow_repository import (
    WorkflowRepository,
    WorkflowVersionRepository,
)
from workflow_platform.repositories.workspace_repository import WorkspaceRepository


class RepositoryRegistry:
    """One instance per unit-of-work session; exposes every repository as
    a lazily-constructed, memoized property so services only pay for the
    repositories they actually touch."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[str, object] = {}

    def _get(self, key: str, cls: type):
        if key not in self._cache:
            self._cache[key] = cls(self.session)
        return self._cache[key]

    @property
    def workspaces(self) -> WorkspaceRepository:
        return self._get("workspaces", WorkspaceRepository)

    @property
    def workflows(self) -> WorkflowRepository:
        return self._get("workflows", WorkflowRepository)

    @property
    def workflow_versions(self) -> WorkflowVersionRepository:
        return self._get("workflow_versions", WorkflowVersionRepository)

    @property
    def node_definitions(self) -> NodeDefinitionRepository:
        return self._get("node_definitions", NodeDefinitionRepository)

    @property
    def workflow_nodes(self) -> WorkflowNodeRepository:
        return self._get("workflow_nodes", WorkflowNodeRepository)

    @property
    def workflow_edges(self) -> WorkflowEdgeRepository:
        return self._get("workflow_edges", WorkflowEdgeRepository)

    @property
    def executions(self) -> ExecutionRepository:
        return self._get("executions", ExecutionRepository)

    @property
    def node_executions(self) -> NodeExecutionRepository:
        return self._get("node_executions", NodeExecutionRepository)

    @property
    def checkpoints(self) -> CheckpointRepository:
        return self._get("checkpoints", CheckpointRepository)

    @property
    def approval_requests(self) -> ApprovalRequestRepository:
        return self._get("approval_requests", ApprovalRequestRepository)

    @property
    def approval_comments(self) -> ApprovalCommentRepository:
        return self._get("approval_comments", ApprovalCommentRepository)

    @property
    def schedules(self) -> ScheduleRepository:
        return self._get("schedules", ScheduleRepository)

    @property
    def events(self) -> EventRepository:
        return self._get("events", EventRepository)

    @property
    def subscriptions(self) -> SubscriptionRepository:
        return self._get("subscriptions", SubscriptionRepository)

    @property
    def webhook_deliveries(self) -> WebhookDeliveryRepository:
        return self._get("webhook_deliveries", WebhookDeliveryRepository)

    @property
    def variables(self) -> VariableRepository:
        return self._get("variables", VariableRepository)

    @property
    def templates(self) -> WorkflowTemplateRepository:
        return self._get("templates", WorkflowTemplateRepository)

    @property
    def permission_grants(self) -> PermissionGrantRepository:
        return self._get("permission_grants", PermissionGrantRepository)

    @property
    def audit_log(self) -> AuditLogEntryRepository:
        return self._get("audit_log", AuditLogEntryRepository)

    @property
    def execution_logs(self) -> ExecutionLogRepository:
        return self._get("execution_logs", ExecutionLogRepository)
