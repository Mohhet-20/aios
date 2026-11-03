"""Column-level security: one rule per resource type naming which
columns are restricted and which role levels may still see them.
`redact_row()` is the enforcement point -- it strips restricted
columns from a row dict unless the caller's role satisfies the rule,
using the same role hierarchy `AnalyticsRbacService` defines (a
caller passes their resolved role level in, this module doesn't look
it up itself, keeping it usable without a live RBAC lookup in tests
or batch jobs)."""
from __future__ import annotations

from analytics_platform.core.exceptions import ValidationError
from analytics_platform.models.security import ColumnLevelSecurityRuleModel
from analytics_platform.repositories.registry import RepositoryRegistry
from analytics_platform.security.rbac_service import ROLE_ORDER, role_satisfies


class ColumnLevelSecurityService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    def _assert_valid_roles(self, allowed_roles: list[str]) -> None:
        for role in allowed_roles:
            if role not in ROLE_ORDER:
                raise ValidationError(f"'{role}' is not a recognized role level")

    async def set_rule(
        self, tenant_id: str, resource_type: str, *, restricted_columns: list[str], allowed_roles: list[str],
    ) -> ColumnLevelSecurityRuleModel:
        self._assert_valid_roles(allowed_roles)
        existing = await self.repos.column_level_rules.get_for_resource(tenant_id, resource_type)
        if existing is not None:
            existing.restricted_columns = restricted_columns
            existing.allowed_roles = allowed_roles
            return await self.repos.column_level_rules.update(existing)
        rule = ColumnLevelSecurityRuleModel(
            tenant_id=tenant_id, resource_type=resource_type, restricted_columns=restricted_columns, allowed_roles=allowed_roles,
        )
        return await self.repos.column_level_rules.add(rule)

    async def get_rule(self, tenant_id: str, resource_type: str) -> ColumnLevelSecurityRuleModel | None:
        return await self.repos.column_level_rules.get_for_resource(tenant_id, resource_type)

    async def redact_row(self, tenant_id: str, resource_type: str, row: dict, *, caller_role: str) -> dict:
        rule = await self.get_rule(tenant_id, resource_type)
        if rule is None:
            return dict(row)
        if any(role_satisfies(caller_role, allowed) for allowed in rule.allowed_roles):
            return dict(row)
        return {key: value for key, value in row.items() if key not in rule.restricted_columns}
