from __future__ import annotations

from sqlalchemy import select

from eval_platform.models.alert import AlertModel, AlertRuleModel
from eval_platform.repositories.base import SQLAlchemyRepository


class AlertRuleRepository(SQLAlchemyRepository[AlertRuleModel]):
    model = AlertRuleModel

    async def list_active_for_workspace(self, workspace_id: str) -> list[AlertRuleModel]:
        stmt = select(AlertRuleModel).where(AlertRuleModel.workspace_id == workspace_id, AlertRuleModel.is_active.is_(True))
        return list((await self.session.execute(stmt)).scalars().all())


class AlertRepository(SQLAlchemyRepository[AlertModel]):
    model = AlertModel

    async def list_for_workspace(self, workspace_id: str, *, status: str | None = None, category: str | None = None) -> list[AlertModel]:
        stmt = select(AlertModel).where(AlertModel.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(AlertModel.status == status)
        if category:
            stmt = stmt.where(AlertModel.category == category)
        stmt = stmt.order_by(AlertModel.triggered_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_open_for_rule(self, alert_rule_id: str) -> list[AlertModel]:
        stmt = select(AlertModel).where(AlertModel.alert_rule_id == alert_rule_id, AlertModel.status != "resolved")
        return list((await self.session.execute(stmt)).scalars().all())
