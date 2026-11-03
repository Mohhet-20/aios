"""In-code catalog of every fine-grained permission and every built-in
role this platform ships with. `PermissionModel`/`RoleModel` rows are
seeded from these constants (`bootstrap.py`) so a Role Manager UI can
query the database without importing Python — but the registry here
is the single source of truth; the DB rows are a projection of it.

Permission keys are `"<resource_type>:<action>"`. A role's `permissions`
list may contain an exact key, `"<resource_type>:manage"` (grants every
action on that resource type), or `"*"` (grants everything — reserved
for the built-in `system_admin` role). This keeps the model genuinely
RBAC today while leaving room to grow into ABAC later: a future
attribute-based rule would slot in as an additional check inside
`AuthorizationService.has_permission` without changing this registry's
shape."""
from __future__ import annotations

from dataclasses import dataclass, field

from identity_platform.domain.enums import PermissionAction, PermissionResourceType, RoleScopeType

WILDCARD_ALL = "*"


def _key(resource_type: PermissionResourceType, action: PermissionAction) -> str:
    return f"{resource_type.value}:{action.value}"


def _manage_key(resource_type: PermissionResourceType) -> str:
    return f"{resource_type.value}:manage"


# Every resource type gets create/read/update/delete/manage; a handful
# get additional actions that are meaningful for them specifically.
_EXTRA_ACTIONS: dict[PermissionResourceType, list[PermissionAction]] = {
    PermissionResourceType.AGENT: [PermissionAction.EXECUTE],
    PermissionResourceType.WORKFLOW: [PermissionAction.EXECUTE],
    PermissionResourceType.TOOL: [PermissionAction.EXECUTE],
    PermissionResourceType.PROMPT: [PermissionAction.EXECUTE],
    PermissionResourceType.ORGANIZATION: [PermissionAction.INVITE],
    PermissionResourceType.WORKSPACE: [PermissionAction.INVITE],
    PermissionResourceType.TEAM: [PermissionAction.INVITE],
    PermissionResourceType.PROJECT: [PermissionAction.INVITE],
    PermissionResourceType.AUDIT: [PermissionAction.APPROVE],
}

_BASE_ACTIONS = [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE, PermissionAction.DELETE, PermissionAction.MANAGE]


@dataclass(frozen=True)
class PermissionDefinition:
    key: str
    resource_type: PermissionResourceType
    action: PermissionAction
    description: str


def _build_permission_registry() -> list[PermissionDefinition]:
    definitions: list[PermissionDefinition] = []
    for resource_type in PermissionResourceType:
        actions = list(_BASE_ACTIONS) + _EXTRA_ACTIONS.get(resource_type, [])
        for action in actions:
            definitions.append(PermissionDefinition(
                key=_key(resource_type, action), resource_type=resource_type, action=action,
                description=f"{action.value.capitalize()} {resource_type.value.replace('_', ' ')} resources",
            ))
    return definitions


PERMISSION_REGISTRY: list[PermissionDefinition] = _build_permission_registry()
PERMISSION_KEYS: frozenset[str] = frozenset(p.key for p in PERMISSION_REGISTRY)


@dataclass(frozen=True)
class BuiltinRoleDefinition:
    slug: str
    name: str
    scope_type: RoleScopeType
    description: str
    permissions: list[str] = field(default_factory=list)


def _all_manage_keys() -> list[str]:
    return [_manage_key(rt) for rt in PermissionResourceType]


BUILTIN_ROLES: list[BuiltinRoleDefinition] = [
    BuiltinRoleDefinition(
        slug="system_admin", name="System Admin", scope_type=RoleScopeType.SYSTEM,
        description="Unrestricted platform-wide access.", permissions=[WILDCARD_ALL],
    ),
    BuiltinRoleDefinition(
        slug="org_owner", name="Organization Owner", scope_type=RoleScopeType.ORGANIZATION,
        description="Full control over an organization, including billing and deletion.", permissions=_all_manage_keys(),
    ),
    BuiltinRoleDefinition(
        slug="org_admin", name="Organization Admin", scope_type=RoleScopeType.ORGANIZATION,
        description="Manages members, roles, and workspaces within an organization.",
        permissions=[
            _manage_key(PermissionResourceType.WORKSPACE), _manage_key(PermissionResourceType.TEAM),
            _manage_key(PermissionResourceType.PROJECT), _manage_key(PermissionResourceType.USER),
            _manage_key(PermissionResourceType.ROLE), _key(PermissionResourceType.ORGANIZATION, PermissionAction.READ),
            _key(PermissionResourceType.ORGANIZATION, PermissionAction.UPDATE),
            _key(PermissionResourceType.ORGANIZATION, PermissionAction.INVITE),
        ],
    ),
    BuiltinRoleDefinition(
        slug="org_member", name="Organization Member", scope_type=RoleScopeType.ORGANIZATION,
        description="Standard member with read access and the ability to work within assigned workspaces.",
        permissions=[
            _key(PermissionResourceType.ORGANIZATION, PermissionAction.READ),
            _key(PermissionResourceType.WORKSPACE, PermissionAction.READ),
            _key(PermissionResourceType.PROJECT, PermissionAction.READ),
        ],
    ),
    BuiltinRoleDefinition(
        slug="org_billing_viewer", name="Billing Viewer", scope_type=RoleScopeType.ORGANIZATION,
        description="Read-only access to organization and billing information.",
        permissions=[_key(PermissionResourceType.ORGANIZATION, PermissionAction.READ)],
    ),
    BuiltinRoleDefinition(
        slug="workspace_admin", name="Workspace Admin", scope_type=RoleScopeType.WORKSPACE,
        description="Manages a workspace's projects, teams, and membership.",
        permissions=[
            _manage_key(PermissionResourceType.PROJECT), _manage_key(PermissionResourceType.TEAM),
            _key(PermissionResourceType.WORKSPACE, PermissionAction.READ),
            _key(PermissionResourceType.WORKSPACE, PermissionAction.UPDATE),
            _key(PermissionResourceType.WORKSPACE, PermissionAction.INVITE),
        ],
    ),
    BuiltinRoleDefinition(
        slug="workspace_member", name="Workspace Member", scope_type=RoleScopeType.WORKSPACE,
        description="Can build and run agents/workflows/prompts/tools within a workspace.",
        permissions=[
            _key(PermissionResourceType.WORKSPACE, PermissionAction.READ),
            _key(PermissionResourceType.PROJECT, PermissionAction.READ),
            _key(PermissionResourceType.AGENT, PermissionAction.CREATE), _key(PermissionResourceType.AGENT, PermissionAction.READ),
            _key(PermissionResourceType.AGENT, PermissionAction.EXECUTE),
            _key(PermissionResourceType.WORKFLOW, PermissionAction.CREATE), _key(PermissionResourceType.WORKFLOW, PermissionAction.READ),
            _key(PermissionResourceType.WORKFLOW, PermissionAction.EXECUTE),
            _key(PermissionResourceType.PROMPT, PermissionAction.CREATE), _key(PermissionResourceType.PROMPT, PermissionAction.READ),
            _key(PermissionResourceType.PROMPT, PermissionAction.EXECUTE),
            _key(PermissionResourceType.TOOL, PermissionAction.READ), _key(PermissionResourceType.TOOL, PermissionAction.EXECUTE),
            _key(PermissionResourceType.MEMORY, PermissionAction.READ), _key(PermissionResourceType.DATASET, PermissionAction.READ),
        ],
    ),
    BuiltinRoleDefinition(
        slug="workspace_viewer", name="Workspace Viewer", scope_type=RoleScopeType.WORKSPACE,
        description="Read-only access to a workspace's resources.",
        permissions=[
            _key(PermissionResourceType.WORKSPACE, PermissionAction.READ), _key(PermissionResourceType.PROJECT, PermissionAction.READ),
            _key(PermissionResourceType.AGENT, PermissionAction.READ), _key(PermissionResourceType.WORKFLOW, PermissionAction.READ),
            _key(PermissionResourceType.PROMPT, PermissionAction.READ),
        ],
    ),
    BuiltinRoleDefinition(
        slug="project_admin", name="Project Admin", scope_type=RoleScopeType.PROJECT,
        description="Full control over a single project's resources.",
        permissions=[
            _key(PermissionResourceType.PROJECT, PermissionAction.READ), _key(PermissionResourceType.PROJECT, PermissionAction.UPDATE),
            _key(PermissionResourceType.PROJECT, PermissionAction.INVITE),
            _manage_key(PermissionResourceType.AGENT), _manage_key(PermissionResourceType.WORKFLOW),
            _manage_key(PermissionResourceType.PROMPT), _manage_key(PermissionResourceType.TOOL),
        ],
    ),
    BuiltinRoleDefinition(
        slug="project_contributor", name="Project Contributor", scope_type=RoleScopeType.PROJECT,
        description="Can create and run resources within a project but not manage membership.",
        permissions=[
            _key(PermissionResourceType.PROJECT, PermissionAction.READ),
            _key(PermissionResourceType.AGENT, PermissionAction.CREATE), _key(PermissionResourceType.AGENT, PermissionAction.EXECUTE),
            _key(PermissionResourceType.WORKFLOW, PermissionAction.CREATE), _key(PermissionResourceType.WORKFLOW, PermissionAction.EXECUTE),
        ],
    ),
]

BUILTIN_ROLE_SLUGS: frozenset[str] = frozenset(r.slug for r in BUILTIN_ROLES)
