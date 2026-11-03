"""Real-time cost tracking, per-entity/category rollups, and budget
enforcement with threshold-crossing alerts."""
from __future__ import annotations


from perf_platform.config.settings import get_settings
from perf_platform.core.exceptions import (
    BudgetExceededError,
    BudgetNotFoundError,
    UnsupportedCostCategoryError,
    UnsupportedCostEntityTypeError,
)
from perf_platform.cost_intelligence.pricing_rules import budget_utilization_pct, crossed_thresholds
from perf_platform.models.cost import BudgetModel, CostAlertModel, CostRecordModel
from perf_platform.repositories.registry import RepositoryRegistry
from perf_platform.clock import utc_now


class CostRecordService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    def _check(self, category: str, entity_type: str) -> None:
        if category not in self.settings.cost_categories:
            raise UnsupportedCostCategoryError(f"Unsupported cost category '{category}'")
        if entity_type not in self.settings.cost_entity_types:
            raise UnsupportedCostEntityTypeError(f"Unsupported cost entity type '{entity_type}'")

    async def record(
        self, tenant_id: str, *, category: str, entity_type: str, entity_id: str,
        amount_usd: float, unit_count: float = 0.0, extra: dict | None = None,
    ) -> CostRecordModel:
        self._check(category, entity_type)
        record = await self.repos.cost_records.add(
            CostRecordModel(
                tenant_id=tenant_id, category=category, entity_type=entity_type, entity_id=entity_id,
                amount_usd=amount_usd, unit_count=unit_count, recorded_at=utc_now(), extra=extra or {},
            )
        )
        await self.repos.session.commit()
        # A cost record can push an entity over budget the moment it lands —
        # check inline so alerts fire in real time rather than on the next poll.
        await BudgetService(self.repos).check_and_alert(tenant_id, entity_type=entity_type, entity_id=entity_id)
        return record

    async def total_for_entity(self, tenant_id: str, entity_type: str, entity_id: str) -> float:
        return await self.repos.cost_records.total_for_entity(tenant_id, entity_type, entity_id)

    async def list_for_tenant(self, tenant_id: str, *, category: str | None = None) -> list[CostRecordModel]:
        return await self.repos.cost_records.list_for_tenant(tenant_id, category=category)


class BudgetService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def set_budget(self, tenant_id: str, *, entity_type: str, entity_id: str, limit_usd: float, period: str = "monthly") -> BudgetModel:
        if entity_type not in self.settings.cost_entity_types:
            raise UnsupportedCostEntityTypeError(f"Unsupported cost entity type '{entity_type}'")
        existing = await self.repos.budgets.get_for_entity(tenant_id, entity_type, entity_id)
        if existing is not None:
            existing.limit_usd = limit_usd
            existing.period = period
            budget = existing
        else:
            budget = await self.repos.budgets.add(
                BudgetModel(tenant_id=tenant_id, entity_type=entity_type, entity_id=entity_id, limit_usd=limit_usd, period=period)
            )
        await self.repos.session.commit()
        return budget

    async def get_budget_or_404(self, tenant_id: str, entity_type: str, entity_id: str) -> BudgetModel:
        budget = await self.repos.budgets.get_for_entity(tenant_id, entity_type, entity_id)
        if budget is None:
            raise BudgetNotFoundError(f"No budget set for {entity_type} '{entity_id}'")
        return budget

    async def utilization_pct(self, tenant_id: str, entity_type: str, entity_id: str) -> float:
        budget = await self.get_budget_or_404(tenant_id, entity_type, entity_id)
        spent = await self.repos.cost_records.total_for_entity(tenant_id, entity_type, entity_id)
        return budget_utilization_pct(spent_usd=spent, limit_usd=budget.limit_usd)

    async def check_and_alert(self, tenant_id: str, *, entity_type: str, entity_id: str) -> list[CostAlertModel]:
        """No-op (not an error) if no budget is configured for this
        entity — budgets are opt-in, not mandatory."""
        budget = await self.repos.budgets.get_for_entity(tenant_id, entity_type, entity_id)
        if budget is None or not budget.is_active:
            return []
        spent = await self.repos.cost_records.total_for_entity(tenant_id, entity_type, entity_id)
        utilization = budget_utilization_pct(spent_usd=spent, limit_usd=budget.limit_usd)
        existing_alerts = await self.repos.cost_alerts.list_for_budget(tenant_id, budget.id)
        already_alerted = [a.threshold_pct for a in existing_alerts]
        new_thresholds = crossed_thresholds(
            utilization_pct=utilization, thresholds_pct=self.settings.budget_alert_thresholds_pct, already_alerted_pct=already_alerted,
        )
        created = []
        for threshold in new_thresholds:
            alert = await self.repos.cost_alerts.add(
                CostAlertModel(
                    tenant_id=tenant_id, budget_id=budget.id, threshold_pct=threshold, spend_usd=spent,
                    message=f"{entity_type} '{entity_id}' has used {utilization:.1f}% of its {budget.period} budget (${spent:.2f} / ${budget.limit_usd:.2f})",
                )
            )
            created.append(alert)
        if created:
            await self.repos.session.commit()
        return created

    async def enforce(self, tenant_id: str, *, entity_type: str, entity_id: str) -> None:
        """Hard stop for callers that want to block further spend once
        a budget is fully exhausted (opt-in — `record()` above only
        alerts, it never blocks, since most callers want visibility
        without an outage risk from a mis-configured budget)."""
        budget = await self.repos.budgets.get_for_entity(tenant_id, entity_type, entity_id)
        if budget is None or not budget.is_active:
            return
        spent = await self.repos.cost_records.total_for_entity(tenant_id, entity_type, entity_id)
        if spent >= budget.limit_usd:
            raise BudgetExceededError(f"{entity_type} '{entity_id}' has exceeded its budget (${spent:.2f} >= ${budget.limit_usd:.2f})")
