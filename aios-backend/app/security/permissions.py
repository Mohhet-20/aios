"""Role-Based Access Control: permission catalog + default role → permission
mapping. Permissions are dotted `resource:action` strings so new
capabilities are additive (define a new string, grant it to a role) rather
than requiring an enum migration.
"""

from enum import Enum


class Permission(str, Enum):
    # Organization / team / user management
    ORG_MANAGE = "organization:manage"
    TEAM_MANAGE = "team:manage"
    USER_MANAGE = "user:manage"
    BILLING_MANAGE = "billing:manage"

    # Agents / prompts / workflows
    AGENT_READ = "agent:read"
    AGENT_WRITE = "agent:write"
    PROMPT_READ = "prompt:read"
    PROMPT_WRITE = "prompt:write"
    PROMPT_PROMOTE = "prompt:promote"
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_WRITE = "workflow:write"
    WORKFLOW_EXECUTE = "workflow:execute"

    # AI Core
    INFERENCE_RUN = "inference:run"
    MODEL_MANAGE = "model:manage"
    EMBEDDING_CREATE = "embedding:create"

    # Data
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_WRITE = "knowledge:write"
    DOCUMENT_READ = "document:read"
    DOCUMENT_WRITE = "document:write"
    DATASET_READ = "dataset:read"
    DATASET_WRITE = "dataset:write"

    # Evaluation / experiments
    EVALUATION_READ = "evaluation:read"
    EVALUATION_WRITE = "evaluation:write"
    EXPERIMENT_READ = "experiment:read"
    EXPERIMENT_WRITE = "experiment:write"

    # Platform / governance
    AUDIT_READ = "audit:read"
    CONFIGURATION_MANAGE = "configuration:manage"
    PLUGIN_MANAGE = "plugin:manage"
    APIKEY_MANAGE = "apikey:manage"


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    SERVICE_ACCOUNT = "service_account"


_ALL_PERMISSIONS = set(Permission)

_READ_ONLY_PERMISSIONS = {p for p in Permission if p.value.endswith(":read")}

_MEMBER_PERMISSIONS = _READ_ONLY_PERMISSIONS | {
    Permission.AGENT_WRITE,
    Permission.PROMPT_WRITE,
    Permission.WORKFLOW_WRITE,
    Permission.WORKFLOW_EXECUTE,
    Permission.INFERENCE_RUN,
    Permission.EMBEDDING_CREATE,
    Permission.MEMORY_WRITE,
    Permission.KNOWLEDGE_WRITE,
    Permission.DOCUMENT_WRITE,
    Permission.DATASET_WRITE,
    Permission.EVALUATION_WRITE,
    Permission.EXPERIMENT_WRITE,
}

_ADMIN_PERMISSIONS = _MEMBER_PERMISSIONS | {
    Permission.TEAM_MANAGE,
    Permission.USER_MANAGE,
    Permission.PROMPT_PROMOTE,
    Permission.MODEL_MANAGE,
    Permission.AUDIT_READ,
    Permission.CONFIGURATION_MANAGE,
    Permission.PLUGIN_MANAGE,
    Permission.APIKEY_MANAGE,
}

ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.OWNER: _ALL_PERMISSIONS,
    Role.ADMIN: _ADMIN_PERMISSIONS,
    Role.MEMBER: _MEMBER_PERMISSIONS,
    Role.VIEWER: _READ_ONLY_PERMISSIONS,
    Role.SERVICE_ACCOUNT: _MEMBER_PERMISSIONS,
}


def permissions_for_role(role: Role) -> list[str]:
    return sorted(p.value for p in ROLE_PERMISSIONS.get(role, set()))


def role_has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
