from __future__ import annotations

from sqlalchemy import select

from eval_platform.models.metric import MetricDefinitionModel, MetricResultModel
from eval_platform.repositories.base import SQLAlchemyRepository


class MetricDefinitionRepository(SQLAlchemyRepository[MetricDefinitionModel]):
    model = MetricDefinitionModel

    async def get_by_key(self, key: str) -> MetricDefinitionModel | None:
        stmt = select(MetricDefinitionModel).where(MetricDefinitionModel.key == key)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_category(self, category: str) -> list[MetricDefinitionModel]:
        stmt = select(MetricDefinitionModel).where(MetricDefinitionModel.category == category)
        return list((await self.session.execute(stmt)).scalars().all())


class MetricResultRepository(SQLAlchemyRepository[MetricResultModel]):
    model = MetricResultModel

    async def list_for_subject(self, subject_type: str, subject_id: str) -> list[MetricResultModel]:
        stmt = select(MetricResultModel).where(MetricResultModel.subject_type == subject_type, MetricResultModel.subject_id == subject_id)
        return list((await self.session.execute(stmt)).scalars().all())
