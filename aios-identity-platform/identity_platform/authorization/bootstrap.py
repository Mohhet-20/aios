"""Seeds `PermissionModel`/`RoleModel` rows from the in-code registry
(`registry.py`). Idempotent — safe to call on every app startup;
existing rows are left alone (a permission/role already in the
database is assumed to be the source of truth for anything an admin
may have since customized, e.g. a role's `description`), only rows
that don't exist yet are inserted."""
from __future__ import annotations

from identity_platform.authorization.registry import BUILTIN_ROLES, PERMISSION_REGISTRY
from identity_platform.models.rbac import PermissionModel, RoleModel
from identity_platform.repositories.registry import RepositoryRegistry


async def seed_permissions(repos: RepositoryRegistry) -> int:
    created = 0
    for definition in PERMISSION_REGISTRY:
        existing = await repos.permissions.get_by_key(definition.key)
        if existing is not None:
            continue
        await repos.permissions.add(PermissionModel(
            key=definition.key, resource_type=definition.resource_type.value,
            action=definition.action.value, description=definition.description,
        ))
        created += 1
    return created


async def seed_builtin_roles(repos: RepositoryRegistry) -> int:
    created = 0
    for definition in BUILTIN_ROLES:
        existing = await repos.roles.get_by_slug(None, definition.slug)
        if existing is not None:
            continue
        await repos.roles.add(RoleModel(
            organization_id=None, scope_type=definition.scope_type.value, name=definition.name,
            slug=definition.slug, description=definition.description, is_custom=False,
            permissions=list(definition.permissions),
        ))
        created += 1
    return created


async def bootstrap_authorization(repos: RepositoryRegistry) -> None:
    await seed_permissions(repos)
    await seed_builtin_roles(repos)

