import pytest

from release_platform.core.exceptions import ConflictError, NotFoundError, UnsupportedFeatureFlagScopeError, ValidationError
from release_platform.feature_flags.feature_flag_service import FeatureFlagOverrideService, FeatureFlagService

pytestmark = pytest.mark.asyncio

TENANT = "t-flags"


async def test_create_flag_rejects_unsupported_scope(repos):
    svc = FeatureFlagService(repos)
    with pytest.raises(UnsupportedFeatureFlagScopeError):
        await svc.create_flag(TENANT, key="x", name="X", scope="galactic")


async def test_create_flag_rejects_duplicate_key(repos):
    svc = FeatureFlagService(repos)
    await svc.create_flag(TENANT, key="new-console", name="New Console")
    with pytest.raises(ConflictError):
        await svc.create_flag(TENANT, key="new-console", name="New Console Again")


async def test_get_or_404_raises_for_missing(repos):
    svc = FeatureFlagService(repos)
    with pytest.raises(NotFoundError):
        await svc.get_or_404(TENANT, "nonexistent-id")


async def test_enable_disable_toggle(repos):
    svc = FeatureFlagService(repos)
    flag = await svc.create_flag(TENANT, key="toggle-me", name="Toggle Me")
    assert flag.enabled is False
    flag = await svc.enable(TENANT, flag.id)
    assert flag.enabled is True
    flag = await svc.disable(TENANT, flag.id)
    assert flag.enabled is False


async def test_set_rollout_pct_validates_range(repos):
    svc = FeatureFlagService(repos)
    flag = await svc.create_flag(TENANT, key="rollout-me", name="Rollout Me")
    with pytest.raises(ValidationError):
        await svc.set_rollout_pct(TENANT, flag.id, rollout_pct=150.0)
    flag = await svc.set_rollout_pct(TENANT, flag.id, rollout_pct=50.0)
    assert flag.rollout_pct == 50.0


async def test_emergency_disable_overrides_everything(repos):
    flag_svc = FeatureFlagService(repos)
    override_svc = FeatureFlagOverrideService(repos)
    flag = await flag_svc.create_flag(TENANT, key="kill-me", name="Kill Me", enabled=True, rollout_pct=100.0)
    await override_svc.set_override(TENANT, flag_id=flag.id, target_ref="user-1", enabled=True)

    await flag_svc.emergency_disable(TENANT, flag.id)
    assert await override_svc.is_enabled_for(TENANT, flag.id, "user-1") is False


async def test_override_takes_precedence_over_base_state(repos):
    flag_svc = FeatureFlagService(repos)
    override_svc = FeatureFlagOverrideService(repos)
    flag = await flag_svc.create_flag(TENANT, key="override-me", name="Override Me", enabled=False)

    assert await override_svc.is_enabled_for(TENANT, flag.id, "user-1") is False
    await override_svc.set_override(TENANT, flag_id=flag.id, target_ref="user-1", enabled=True)
    assert await override_svc.is_enabled_for(TENANT, flag.id, "user-1") is True


async def test_disabled_base_flag_short_circuits_rollout(repos):
    flag_svc = FeatureFlagService(repos)
    override_svc = FeatureFlagOverrideService(repos)
    flag = await flag_svc.create_flag(TENANT, key="disabled-rollout", name="Disabled Rollout", enabled=False, rollout_pct=100.0)
    assert await override_svc.is_enabled_for(TENANT, flag.id, "user-1") is False


async def test_full_rollout_enabled_flag_is_true_for_all(repos):
    flag_svc = FeatureFlagService(repos)
    override_svc = FeatureFlagOverrideService(repos)
    flag = await flag_svc.create_flag(TENANT, key="full-rollout", name="Full Rollout", enabled=True, rollout_pct=100.0)
    assert await override_svc.is_enabled_for(TENANT, flag.id, "user-1") is True
    assert await override_svc.is_enabled_for(TENANT, flag.id, "user-2") is True


async def test_set_override_upserts(repos):
    flag_svc = FeatureFlagService(repos)
    override_svc = FeatureFlagOverrideService(repos)
    flag = await flag_svc.create_flag(TENANT, key="upsert-me", name="Upsert Me")
    await override_svc.set_override(TENANT, flag_id=flag.id, target_ref="org:acme", enabled=True)
    await override_svc.set_override(TENANT, flag_id=flag.id, target_ref="org:acme", enabled=False)
    overrides = await override_svc.list_overrides(TENANT, flag.id)
    assert len(overrides) == 1
    assert overrides[0].enabled is False
