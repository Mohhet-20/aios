from __future__ import annotations

from sqlalchemy import func, select

from eval_platform.models.evaluation import EvaluationModel, EvaluationVersionModel
from eval_platform.repositories.base import SQLAlchemyRepository


class EvaluationRepository(SQLAlchemyRepository[EvaluationModel]):
    model = EvaluationModel

    async def list_for_workspace(self, workspace_id: str, *, status: str | None = None, category: str | None = None) -> list[EvaluationModel]:
        stmt = select(EvaluationModel).where(EvaluationModel.workspace_id == workspace_id, EvaluationModel.is_deleted.is_(False))
        if status:
            stmt = stmt.where(EvaluationModel.status == status)
        if category:
            stmt = stmt.where(EvaluationModel.category == category)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_slug(self, workspace_id: str, slug: str) -> EvaluationModel | None:
        stmt = select(EvaluationModel).where(
            EvaluationModel.workspace_id == workspace_id, EvaluationModel.slug == slug, EvaluationModel.is_deleted.is_(False)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def search(self, workspace_id: str, query: str, *, limit: int = 50) -> list[EvaluationModel]:
        pattern = f"%{query.lower()}%"
        stmt = select(EvaluationModel).where(
            EvaluationModel.workspace_id == workspace_id, EvaluationModel.is_deleted.is_(False),
            func.lower(EvaluationModel.name).like(pattern),
        ).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class EvaluationVersionRepository(SQLAlchemyRepository[EvaluationVersionModel]):
    model = EvaluationVersionModel

    async def list_for_evaluation(self, evaluation_id: str) -> list[EvaluationVersionModel]:
        stmt = select(EvaluationVersionModel).where(EvaluationVersionModel.evaluation_id == evaluation_id).order_by(EvaluationVersionModel.version_number.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_latest_draft(self, evaluation_id: str) -> EvaluationVersionModel | None:
        stmt = select(EvaluationVersionModel).where(
            EvaluationVersionModel.evaluation_id == evaluation_id, EvaluationVersionModel.status == "draft",
        ).order_by(EvaluationVersionModel.version_number.desc())
        return (await self.session.execute(stmt)).scalars().first()

    async def get_max_version_number(self, evaluation_id: str) -> int:
        stmt = select(EvaluationVersionModel.version_number).where(EvaluationVersionModel.evaluation_id == evaluation_id).order_by(EvaluationVersionModel.version_number.desc())
        result = (await self.session.execute(stmt)).scalars().first()
        return result or 0
