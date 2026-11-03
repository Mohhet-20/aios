from __future__ import annotations

from sqlalchemy import select

from security_platform.models.guardrails import GuardrailEvaluationModel, GuardrailRuleModel, GuardrailViolationModel
from security_platform.repositories.base import SQLAlchemyRepository


class GuardrailRuleRepository(SQLAlchemyRepository[GuardrailRuleModel]):
    model = GuardrailRuleModel

    async def list_enabled_for_category(self, tenant_id: str, category: str) -> list[GuardrailRuleModel]:
        stmt = select(GuardrailRuleModel).where(
            GuardrailRuleModel.tenant_id == tenant_id,
            GuardrailRuleModel.category == category,
            GuardrailRuleModel.is_deleted.is_(False),
            GuardrailRuleModel.is_enabled.is_(True),
        )
        return list((await self.session.execute(stmt)).scalars().all())


class GuardrailEvaluationRepository(SQLAlchemyRepository[GuardrailEvaluationModel]):
    model = GuardrailEvaluationModel

    async def list_recent(self, tenant_id: str, *, category: str | None = None, limit: int = 200) -> list[GuardrailEvaluationModel]:
        stmt = select(GuardrailEvaluationModel).where(GuardrailEvaluationModel.tenant_id == tenant_id)
        if category:
            stmt = stmt.where(GuardrailEvaluationModel.category == category)
        stmt = stmt.order_by(GuardrailEvaluationModel.evaluated_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_action(self, tenant_id: str) -> dict[str, int]:
        from sqlalchemy import func

        stmt = (
            select(GuardrailEvaluationModel.action_taken, func.count())
            .where(GuardrailEvaluationModel.tenant_id == tenant_id)
            .group_by(GuardrailEvaluationModel.action_taken)
        )
        rows = (await self.session.execute(stmt)).all()
        return {action: count for action, count in rows}


class GuardrailViolationRepository(SQLAlchemyRepository[GuardrailViolationModel]):
    model = GuardrailViolationModel

    async def list_by_status(self, tenant_id: str, status: str, *, limit: int = 200) -> list[GuardrailViolationModel]:
        stmt = (
            select(GuardrailViolationModel)
            .where(GuardrailViolationModel.tenant_id == tenant_id, GuardrailViolationModel.status == status)
            .order_by(GuardrailViolationModel.detected_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_category(self, tenant_id: str) -> dict[str, int]:
        from sqlalchemy import func

        stmt = (
            select(GuardrailViolationModel.category, func.count())
            .where(GuardrailViolationModel.tenant_id == tenant_id)
            .group_by(GuardrailViolationModel.category)
        )
        rows = (await self.session.execute(stmt)).all()
        return {cat: count for cat, count in rows}
