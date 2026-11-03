"""Import every model module so `Base.metadata` is fully populated before
`init_models()`/Alembic ever runs."""
from agent_platform.models.workspace import WorkspaceModel
from agent_platform.models.agent_type import AgentTypeModel
from agent_platform.models.agent import AgentModel
from agent_platform.models.tool_permission import AgentToolPermissionModel
from agent_platform.models.task import TaskModel, TaskDependencyModel
from agent_platform.models.delegation import DelegationModel
from agent_platform.models.execution import AgentExecutionModel, ExecutionCheckpointModel
from agent_platform.models.message import MessageModel, SharedWorkspaceEntryModel
from agent_platform.models.reasoning import ReasoningTraceModel, ReflectionModel
from agent_platform.models.governance import ApprovalGateModel, AuditLogEntryModel, PermissionGrantModel

__all__ = [
    "WorkspaceModel",
    "AgentTypeModel",
    "AgentModel",
    "AgentToolPermissionModel",
    "TaskModel", "TaskDependencyModel",
    "DelegationModel",
    "AgentExecutionModel", "ExecutionCheckpointModel",
    "MessageModel", "SharedWorkspaceEntryModel",
    "ReasoningTraceModel", "ReflectionModel",
    "ApprovalGateModel", "AuditLogEntryModel", "PermissionGrantModel",
]
