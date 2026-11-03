from __future__ import annotations

from sqlalchemy import select

from security_platform.models.risk import RiskScoreModel
from security_platform.repositories.base import SQLAlchemyRepository


class RiskScoreRepository(SQLAlchemyRepository[RiskScoreModel]):
    model = RiskScoreModel

    async def latest_for_entity(self, tenant_id: str, entity_type: str, entity_id: str) -> RiskScoreModel | None:
        stmt = (
            select(RiskScoreModel)
            .where(RiskScoreModel.tenant_id == tenant_id, RiskScoreModel.entity_type == entity_type, RiskScoreModel.entity_id == entity_id)
            .order_by(RiskScoreModel.computed_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def history_for_entity(self, tenant_id: str, entity_type: str, entity_id: str, *, limit: int = 100) -> list[RiskScoreModel]:
        stmt = (
            select(RiskScoreModel)
            .where(RiskScoreModel.tenant_id == tenant_id, RiskScoreModel.entity_type == entity_type, RiskScoreModel.entity_id == entity_id)
            .order_by(RiskScoreModel.computed_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_highest_current(self, tenant_id: str, entity_type: str, *, limit: int = 20) -> list[RiskScoreModel]:
        """Latest score per entity of a given type, sorted descending —
        used for a "top risky entities" view. Same N-simple-queries
        tradeoff as the Observability Platform's `latest_per_component`:
        entity counts here are small enough that this stays well within
        budget while remaining trivially correct."""
        stmt = select(RiskScoreModel.entity_id).where(
            RiskScoreModel.tenant_id == tenant_id, RiskScoreModel.entity_type == entity_type
        ).distinct()
        entity_ids = [row[0] for row in (await self.session.execute(stmt)).all()]
        latest = []
        for entity_id in entity_ids:
            score = await self.latest_for_entity(tenant_id, entity_type, entity_id)
            if score is not None:
                latest.append(score)
        latest.sort(key=lambda s: s.score, reverse=True)
        return latest[:limit]
