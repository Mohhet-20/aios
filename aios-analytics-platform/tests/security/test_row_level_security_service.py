from __future__ import annotations

import pytest

from analytics_platform.core.exceptions import RowLevelSecurityViolationError, ValidationError
from analytics_platform.security.row_level_security_service import RowLevelSecurityService

TENANT = "rls-tenant"


@pytest.mark.asyncio
async def test_set_rule_rejects_bad_mode(repos):
    service = RowLevelSecurityService(repos)
    with pytest.raises(ValidationError):
        await service.set_rule(TENANT, "dashboards", mode="not_a_mode")


@pytest.mark.asyncio
async def test_set_rule_is_upsert(repos):
    service = RowLevelSecurityService(repos)
    a = await service.set_rule(TENANT, "dashboards", mode="tenant_scoped")
    b = await service.set_rule(TENANT, "dashboards", mode="workspace_scoped")
    assert a.id == b.id
    rule = await service.get_rule(TENANT, "dashboards")
    assert rule.mode == "workspace_scoped"


@pytest.mark.asyncio
async def test_enforce_default_mode_is_tenant_scoped(repos):
    service = RowLevelSecurityService(repos)
    # no rule configured -- defaults to tenant_scoped
    await service.enforce(TENANT, "dashboards", row_tenant_id=TENANT)
    with pytest.raises(RowLevelSecurityViolationError):
        await service.enforce(TENANT, "dashboards", row_tenant_id="other-tenant")


@pytest.mark.asyncio
async def test_enforce_unrestricted_allows_cross_tenant(repos):
    service = RowLevelSecurityService(repos)
    await service.set_rule(TENANT, "public_benchmarks", mode="unrestricted")
    await service.enforce(TENANT, "public_benchmarks", row_tenant_id="other-tenant")


@pytest.mark.asyncio
async def test_enforce_workspace_scoped(repos):
    service = RowLevelSecurityService(repos)
    await service.set_rule(TENANT, "workspace_reports", mode="workspace_scoped")
    await service.enforce(
        TENANT, "workspace_reports", row_tenant_id=TENANT, row_workspace_id="ws-1", caller_workspace_id="ws-1",
    )
    with pytest.raises(RowLevelSecurityViolationError):
        await service.enforce(
            TENANT, "workspace_reports", row_tenant_id=TENANT, row_workspace_id="ws-1", caller_workspace_id="ws-2",
        )
