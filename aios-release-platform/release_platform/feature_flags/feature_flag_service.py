"""Feature Flag Platform: toggles across the 5 declared scopes
(global, organization, workspace, user, experiment), a base
enabled/rollout-percentage state guarded directly here (a "simple
status field" resource — no dedicated domain entity, the same
precedent used across every other AIOS platform for resources whose
lifecycle is just a couple of independent fields), per-target
overrides that take precedence over the base state, and an emergency
kill switch that force-disables a flag regardless of its rollout
configuration."""
from __future__ import annotations

from release_platform.config.settings import get_settings
from release_platform.core.exceptions import ConflictError, FeatureFlagNotFoundError, UnsupportedFeatureFlagScopeError, ValidationError
from release_platform.feature_flags.targeting_rules import is_in_rollout
from release_platform.models.feature_flag import FeatureFlagModel, FeatureFlagOverrideModel
from release_platform.repositories.registry import RepositoryRegistry


class FeatureFlagService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, flag_id: str) -> FeatureFlagModel:
        flag = await self.repos.feature_flags.get_or_404(flag_id)
        if flag.tenant_id != tenant_id:
            raise FeatureFlagNotFoundError(f"Feature flag '{flag_id}' not found for tenant '{tenant_id}'")
        return flag

    async def create_flag(
        self, tenant_id: str, *, key: str, name: str, scope: str = "global",
        enabled: bool = False, rollout_pct: float = 0.0, description: str = "",
    ) -> FeatureFlagModel:
        if scope not in self.settings.feature_flag_scopes:
            raise UnsupportedFeatureFlagScopeError(f"Unsupported feature flag scope '{scope}'")
        if await self.repos.feature_flags.get_by_key(tenant_id, key) is not None:
            raise ConflictError(f"Feature flag '{key}' already exists for tenant '{tenant_id}'")
        flag = FeatureFlagModel(
            tenant_id=tenant_id, key=key, name=name, scope=scope,
            enabled=enabled, rollout_pct=rollout_pct, description=description,
        )
        return await self.repos.feature_flags.add(flag)

    async def enable(self, tenant_id: str, flag_id: str) -> FeatureFlagModel:
        flag = await self.get_or_404(tenant_id, flag_id)
        flag.enabled = True
        return flag

    async def disable(self, tenant_id: str, flag_id: str) -> FeatureFlagModel:
        flag = await self.get_or_404(tenant_id, flag_id)
        flag.enabled = False
        return flag

    async def emergency_disable(self, tenant_id: str, flag_id: str) -> FeatureFlagModel:
        """Kill switch: force the flag off and mark it as having been
        killed, regardless of rollout percentage or per-target
        overrides — `is_enabled_for` short-circuits to False whenever
        `is_kill_switch` is set."""
        flag = await self.get_or_404(tenant_id, flag_id)
        flag.enabled = False
        flag.is_kill_switch = True
        return flag

    async def set_rollout_pct(self, tenant_id: str, flag_id: str, *, rollout_pct: float) -> FeatureFlagModel:
        if not (0.0 <= rollout_pct <= 100.0):
            raise ValidationError("rollout_pct must be between 0 and 100")
        flag = await self.get_or_404(tenant_id, flag_id)
        flag.rollout_pct = rollout_pct
        return flag

    async def list_flags(self, tenant_id: str, *, scope: str | None = None) -> list[FeatureFlagModel]:
        return await self.repos.feature_flags.list_for_tenant(tenant_id, scope=scope)


class FeatureFlagOverrideService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.flags = FeatureFlagService(repos)

    async def set_override(
        self, tenant_id: str, *, flag_id: str, target_ref: str, enabled: bool, config_overrides: dict | None = None
    ) -> FeatureFlagOverrideModel:
        await self.flags.get_or_404(tenant_id, flag_id)
        existing = await self.repos.feature_flag_overrides.get_for_target(tenant_id, flag_id, target_ref)
        if existing is not None:
            existing.enabled = enabled
            existing.config_overrides = config_overrides or {}
            return existing
        override = FeatureFlagOverrideModel(
            tenant_id=tenant_id, flag_id=flag_id, target_ref=target_ref, enabled=enabled, config_overrides=config_overrides or {},
        )
        return await self.repos.feature_flag_overrides.add(override)

    async def list_overrides(self, tenant_id: str, flag_id: str) -> list[FeatureFlagOverrideModel]:
        return await self.repos.feature_flag_overrides.list_for_flag(tenant_id, flag_id)

    async def is_enabled_for(self, tenant_id: str, flag_id: str, target_ref: str) -> bool:
        """Evaluation order: kill switch always wins (off), then a
        per-target override always wins over the base state, then the
        base enabled flag gates whether rollout percentage applies at
        all, then the deterministic percentage bucket decides."""
        flag = await self.flags.get_or_404(tenant_id, flag_id)
        if flag.is_kill_switch:
            return False
        override = await self.repos.feature_flag_overrides.get_for_target(tenant_id, flag_id, target_ref)
        if override is not None:
            return override.enabled
        if not flag.enabled:
            return False
        return is_in_rollout(flag.key, target_ref, rollout_pct=flag.rollout_pct)
