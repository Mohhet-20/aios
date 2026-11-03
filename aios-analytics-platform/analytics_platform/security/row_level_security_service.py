"""Row-level security: one rule per resource type controlling whether
a caller may only see rows scoped to their own tenant, their own
workspace, or (rare, disclosed-as-such) rows unrestricted by tenant at
all. `set_rule`/`get_rule` manage the rule; `enforce()` is what a
query path calls before returning rows -- it raises rather than
silently filtering, since a row-level violation getting through is a
real data leak, not a UI nicety."""
from __future__ import annotations

from analytics_platform.core.exceptions import RowLevelSecurityViolationError, ValidationError
from analytics_platform.domain.enums import RowLevelSecurityMode
from analytics_platform.models.security import RowLevelSecurityRuleModel
from analytics_platform.repositories.registry import RepositoryRegistry


class RowLevelSecurityService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    def _assert_valid_mode(self, mode: str) -> None:
        if mode not in {m.value for m in RowLevelSecurityMode}:
            raise ValidationError(f"'{mode}' is not a recognized row-level security mode")

    async def set_rule(
        self, tenant_id: str, resource_type: str, *, mode: str = "tenant_scoped", rule_expression: dict | None = None,
    ) -> RowLevelSecurityRuleModel:
        self._assert_valid_mode(mode)
        existing = await self.repos.row_level_rules.get_for_resource(tenant_id, resource_type)
        if existing is not None:
            existing.mode = mode
            existing.rule_expression = rule_expression or {}
            return await self.repos.row_level_rules.update(existing)
        rule = RowLevelSecurityRuleModel(
            tenant_id=tenant_id, resource_type=resource_type, mode=mode, rule_expression=rule_expression or {},
        )
        return await self.repos.row_level_rules.add(rule)

    async def get_rule(self, tenant_id: str, resource_type: str) -> RowLevelSecurityRuleModel | None:
        return await self.repos.row_level_rules.get_for_resource(tenant_id, resource_type)

    async def enforce(
        self, tenant_id: str, resource_type: str, *, row_tenant_id: str, row_workspace_id: str | None = None,
        caller_workspace_id: str | None = None,
    ) -> None:
        """Raises `RowLevelSecurityViolationError` if the row shouldn't
        be visible to this tenant/workspace under the resource's
        configured rule. No rule configured for a resource type
        defaults to tenant-scoped -- fail toward the safer default,
        not toward unrestricted access."""
        rule = await self.get_rule(tenant_id, resource_type)
        mode = rule.mode if rule is not None else "tenant_scoped"

        if mode == "unrestricted":
            return
        if row_tenant_id != tenant_id:
            raise RowLevelSecurityViolationError(
                f"row belongs to tenant '{row_tenant_id}', caller is scoped to tenant '{tenant_id}'"
            )
        if mode == "workspace_scoped" and row_workspace_id != caller_workspace_id:
            raise RowLevelSecurityViolationError(
                f"row belongs to workspace '{row_workspace_id}', caller is scoped to workspace '{caller_workspace_id}'"
            )
