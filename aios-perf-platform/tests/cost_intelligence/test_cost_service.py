from __future__ import annotations

import pytest

from perf_platform.core.exceptions import BudgetExceededError, BudgetNotFoundError, UnsupportedCostCategoryError
from perf_platform.cost_intelligence.cost_service import BudgetService, CostRecordService

TENANT = "t-cost"


@pytest.mark.asyncio
async def test_record_and_total(repos):
    svc = CostRecordService(repos)
    await svc.record(TENANT, category="token", entity_type="agent", entity_id="agent-1", amount_usd=1.25, unit_count=500)
    await svc.record(TENANT, category="token", entity_type="agent", entity_id="agent-1", amount_usd=2.75, unit_count=1200)
    total = await svc.total_for_entity(TENANT, "agent", "agent-1")
    assert total == 4.0


@pytest.mark.asyncio
async def test_record_rejects_unsupported_category(repos):
    svc = CostRecordService(repos)
    with pytest.raises(UnsupportedCostCategoryError):
        await svc.record(TENANT, category="not-a-category", entity_type="agent", entity_id="a", amount_usd=1.0)


@pytest.mark.asyncio
async def test_budget_not_found(repos):
    svc = BudgetService(repos)
    with pytest.raises(BudgetNotFoundError):
        await svc.get_budget_or_404(TENANT, "user", "no-such-user")


@pytest.mark.asyncio
async def test_budget_utilization_and_alerts(repos):
    budget_svc = BudgetService(repos)
    cost_svc = CostRecordService(repos)
    await budget_svc.set_budget(TENANT, entity_type="workflow", entity_id="wf-1", limit_usd=100.0)

    await cost_svc.record(TENANT, category="infrastructure", entity_type="workflow", entity_id="wf-1", amount_usd=55.0)
    utilization = await budget_svc.utilization_pct(TENANT, "workflow", "wf-1")
    assert utilization == 55.0

    alerts = await repos.cost_alerts.list_for_budget(TENANT, (await budget_svc.get_budget_or_404(TENANT, "workflow", "wf-1")).id)
    assert any(a.threshold_pct == 50.0 for a in alerts)


@pytest.mark.asyncio
async def test_enforce_raises_once_budget_exhausted(repos):
    budget_svc = BudgetService(repos)
    cost_svc = CostRecordService(repos)
    await budget_svc.set_budget(TENANT, entity_type="organization", entity_id="org-1", limit_usd=10.0)
    await cost_svc.record(TENANT, category="gpu", entity_type="organization", entity_id="org-1", amount_usd=12.0)

    with pytest.raises(BudgetExceededError):
        await budget_svc.enforce(TENANT, entity_type="organization", entity_id="org-1")


@pytest.mark.asyncio
async def test_enforce_noop_when_no_budget(repos):
    budget_svc = BudgetService(repos)
    await budget_svc.enforce(TENANT, entity_type="user", entity_id="no-budget-user")  # should not raise
