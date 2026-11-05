"""Import every ORM model so `Base.metadata` is fully populated before
`create_all()` runs — the same explicit-import pattern every other AIOS
services's models package uses."""
from tool_platform.models.checkpoint import ExecutionCheckpointModel
from tool_platform.models.credential import CredentialModel, ToolCredentialBindingModel
from tool_platform.models.discovery import ToolFavoriteModel
from tool_platform.models.execution import ToolExecutionModel
from tool_platform.models.governance import ApprovalGateModel, AuditLogEntryModel, PermissionGrantModel
from tool_platform.models.observability import ExecutionLogModel
from tool_platform.models.plugin import PluginDependencyModel, PluginInstallationModel, PluginModel
from tool_platform.models.schedule import ToolScheduleModel
from tool_platform.models.tool import ToolModel, ToolVersionModel
from tool_platform.models.workspace import WorkspaceModel

__all__ = [
    "WorkspaceModel",
    "ToolModel",
    "ToolVersionModel",
    "PluginModel",
    "PluginDependencyModel",
    "PluginInstallationModel",
    "CredentialModel",
    "ToolCredentialBindingModel",
    "ToolExecutionModel",
    "ExecutionCheckpointModel",
    "ToolScheduleModel",
    "PermissionGrantModel",
    "ApprovalGateModel",
    "AuditLogEntryModel",
    "ExecutionLogModel",
    "ToolFavoriteModel",
]
