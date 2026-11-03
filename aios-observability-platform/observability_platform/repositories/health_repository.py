from __future__ import annotations

from sqlalchemy import select

from observability_platform.models.health import HealthCheckResultModel
from observability_platform.repositories.base import SQLAlchemyRepository


class HealthCheckResultRepository(SQLAlchemyRepository[HealthCheckResultModel]):
    model = HealthCheckResultModel

    async def latest_for_component(self, tenant_id: str, component_id: str) -> HealthCheckResultModel | None:
        stmt = (
            select(HealthCheckResultModel)
            .where(HealthCheckResultModel.tenant_id == tenant_id, HealthCheckResultModel.component_id == component_id)
            .order_by(HealthCheckResultModel.checked_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def latest_per_component(self, tenant_id: str, component_ids: list[str]) -> dict[str, HealthCheckResultModel]:
        """One query per component rather than a single correlated
        subquery — SQLite's support for `DISTINCT ON`-style "latest row
        per group" is awkward, and component counts here are small
        enough (tens, not millions) that N simple queries stay well
        within budget while remaining trivially correct."""
        out: dict[str, HealthCheckResultModel] = {}
        for component_id in component_ids:
            latest = await self.latest_for_component(tenant_id, component_id)
            if latest is not None:
                out[component_id] = latest
        return out

    async def history_for_component(
        self, tenant_id: str, component_id: str, *, limit: int = 100
    ) -> list[HealthCheckResultModel]:
        stmt = (
            select(HealthCheckResultModel)
            .where(HealthCheckResultModel.tenant_id == tenant_id, HealthCheckResultModel.component_id == component_id)
            .order_by(HealthCheckResultModel.checked_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())
