from __future__ import annotations

from sqlalchemy import func, select

from perf_platform.models.cost import BudgetModel, CostAlertModel, CostRecordModel
from perf_platform.repositories.base import SQLAlchemyRepository


class CostRecordRepository(SQLAlchemyRepository[CostRecordModel]):
    model = CostRecordModel

    async def list_for_entity(self, tenant_id: str, entity_type: str, entity_id: str, *, limit: int = 200) -> list[CostRecordModel]:
        stmt = select(CostRecordModel).where(
            CostRecordModel.tenant_id == tenant_id, CostRecordModel.entity_type == entity_type,
            CostRecordModel.entity_id == entity_id,
        ).order_by(CostRecordModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def total_for_entity(self, tenant_id: str, entity_type: str, entity_id: str) -> float:
        stmt = select(func.coalesce(func.sum(CostRecordModel.amount_usd), 0.0)).where(
            CostRecordModel.tenant_id == tenant_id, CostRecordModel.entity_type == entity_type,
            CostRecordModel.entity_id == entity_id,
        )
        return float((await self.session.execute(stmt)).scalar_one())

    async def list_for_tenant(self, tenant_id: str, *, category: str | None = None, limit: int = 200) -> list[CostRecordModel]:
        stmt = select(CostRecordModel).where(CostRecordModel.tenant_id == tenant_id)
        if category:
            stmt = stmt.where(CostRecordModel.category == category)
        stmt = stmt.order_by(CostRecordModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class BudgetRepository(SQLAlchemyRepository[BudgetModel]):
    model = BudgetModel

    async def get_for_entity(self, tenant_id: str, entity_type: str, entity_id: str) -> BudgetModel | None:
        stmt = select(BudgetModel).where(
            BudgetModel.tenant_id == tenant_id, BudgetModel.entity_type == entity_type,
            BudgetModel.entity_id == entity_id, BudgetModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()


class CostAlertRepository(SQLAlchemyRepository[CostAlertModel]):
    model = CostAlertModel

    async def list_for_budget(self, tenant_id: str, budget_id: str) -> list[CostAlertModel]:
        stmt = select(CostAlertModel).where(CostAlertModel.tenant_id == tenant_id, CostAlertModel.budget_id == budget_id)
        return list((await self.session.execute(stmt)).scalars().all())
