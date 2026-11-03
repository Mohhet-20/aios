"""Import every ORM model so `Base.metadata` is fully populated before
`create_all()` runs — the same explicit-import pattern every prior AIOS
platform's models package uses."""
from workflow_platform.models.approval import ApprovalCommentModel, ApprovalRequestModel
from workflow_platform.models.checkpoint import CheckpointModel
from workflow_platform.models.events import EventModel, SubscriptionModel, WebhookDeliveryModel
from workflow_platform.models.execution import ExecutionModel, NodeExecutionModel
from workflow_platform.models.governance import AuditLogEntryModel, PermissionGrantModel
from workflow_platform.models.node import WorkflowEdgeModel, WorkflowNodeModel
from workflow_platform.models.node_definition import NodeDefinitionModel
from workflow_platform.models.observability import ExecutionLogModel
from workflow_platform.models.schedule import ScheduleModel
from workflow_platform.models.template import WorkflowTemplateModel
from workflow_platform.models.variable import VariableModel
from workflow_platform.models.workflow import WorkflowModel, WorkflowVersionModel
from workflow_platform.models.workspace import WorkspaceModel

__all__ = [
    "WorkspaceModel",
    "WorkflowModel",
    "WorkflowVersionModel",
    "NodeDefinitionModel",
    "WorkflowNodeModel",
    "WorkflowEdgeModel",
    "ExecutionModel",
    "NodeExecutionModel",
    "CheckpointModel",
    "ApprovalRequestModel",
    "ApprovalCommentModel",
    "ScheduleModel",
    "EventModel",
    "SubscriptionModel",
    "WebhookDeliveryModel",
    "VariableModel",
    "WorkflowTemplateModel",
    "PermissionGrantModel",
    "AuditLogEntryModel",
    "ExecutionLogModel",
]
