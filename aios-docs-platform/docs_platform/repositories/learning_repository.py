from __future__ import annotations

from sqlalchemy import select

from docs_platform.models.learning import EnrollmentModel, LearningPathModel, TutorialModel
from docs_platform.repositories.base import SQLAlchemyRepository


class TutorialRepository(SQLAlchemyRepository[TutorialModel]):
    model = TutorialModel

    async def list_for_tenant(self, tenant_id: str, *, role: str | None = None, tutorial_type: str | None = None) -> list[TutorialModel]:
        stmt = select(TutorialModel).where(TutorialModel.tenant_id == tenant_id, TutorialModel.is_deleted.is_(False))
        if role:
            stmt = stmt.where(TutorialModel.role == role)
        if tutorial_type:
            stmt = stmt.where(TutorialModel.tutorial_type == tutorial_type)
        return list((await self.session.execute(stmt)).scalars().all())


class LearningPathRepository(SQLAlchemyRepository[LearningPathModel]):
    model = LearningPathModel

    async def list_for_tenant(self, tenant_id: str, *, role: str | None = None) -> list[LearningPathModel]:
        stmt = select(LearningPathModel).where(LearningPathModel.tenant_id == tenant_id, LearningPathModel.is_deleted.is_(False))
        if role:
            stmt = stmt.where(LearningPathModel.role == role)
        return list((await self.session.execute(stmt)).scalars().all())


class EnrollmentRepository(SQLAlchemyRepository[EnrollmentModel]):
    model = EnrollmentModel

    async def get_for_user_and_tutorial(self, tenant_id: str, user_id: str, tutorial_id: str) -> EnrollmentModel | None:
        stmt = select(EnrollmentModel).where(
            EnrollmentModel.tenant_id == tenant_id, EnrollmentModel.user_id == user_id, EnrollmentModel.tutorial_id == tutorial_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_for_user_and_path(self, tenant_id: str, user_id: str, learning_path_id: str) -> EnrollmentModel | None:
        stmt = select(EnrollmentModel).where(
            EnrollmentModel.tenant_id == tenant_id, EnrollmentModel.user_id == user_id, EnrollmentModel.learning_path_id == learning_path_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_user(self, tenant_id: str, user_id: str) -> list[EnrollmentModel]:
        stmt = select(EnrollmentModel).where(EnrollmentModel.tenant_id == tenant_id, EnrollmentModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())
