from __future__ import annotations

from sqlalchemy import select

from prompt_platform.models.version import (
    PromptDependencyModel,
    PromptHistoryModel,
    PromptReleaseModel,
    PromptVersionModel,
)
from prompt_platform.repositories.base import SQLAlchemyRepository


class PromptVersionRepository(SQLAlchemyRepository[PromptVersionModel]):
    model = PromptVersionModel

    async def list_for_prompt(self, prompt_id: str) -> list[PromptVersionModel]:
        stmt = select(PromptVersionModel).where(
            PromptVersionModel.prompt_id == prompt_id, PromptVersionModel.is_deleted.is_(False)
        ).order_by(PromptVersionModel.version_number)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_number(self, prompt_id: str, version_number: int) -> PromptVersionModel | None:
        stmt = select(PromptVersionModel).where(
            PromptVersionModel.prompt_id == prompt_id, PromptVersionModel.version_number == version_number
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_by_branch(self, prompt_id: str, branch: str) -> PromptVersionModel | None:
        stmt = select(PromptVersionModel).where(
            PromptVersionModel.prompt_id == prompt_id, PromptVersionModel.branch == branch,
            PromptVersionModel.is_deleted.is_(False),
        ).order_by(PromptVersionModel.version_number.desc())
        return (await self.session.execute(stmt)).scalars().first()


class PromptDependencyRepository(SQLAlchemyRepository[PromptDependencyModel]):
    model = PromptDependencyModel

    async def list_for_prompt(self, prompt_id: str) -> list[PromptDependencyModel]:
        stmt = select(PromptDependencyModel).where(PromptDependencyModel.prompt_id == prompt_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def all_edges(self) -> list[tuple[str, str]]:
        stmt = select(PromptDependencyModel.prompt_id, PromptDependencyModel.depends_on_prompt_id)
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]


class PromptHistoryRepository(SQLAlchemyRepository[PromptHistoryModel]):
    model = PromptHistoryModel

    async def list_for_prompt(self, prompt_id: str, *, limit: int = 100) -> list[PromptHistoryModel]:
        stmt = (
            select(PromptHistoryModel)
            .where(PromptHistoryModel.prompt_id == prompt_id)
            .order_by(PromptHistoryModel.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class PromptReleaseRepository(SQLAlchemyRepository[PromptReleaseModel]):
    model = PromptReleaseModel

    async def list_for_prompt(self, prompt_id: str) -> list[PromptReleaseModel]:
        stmt = select(PromptReleaseModel).where(PromptReleaseModel.prompt_id == prompt_id).order_by(
            PromptReleaseModel.released_at.desc()
        )
        return list((await self.session.execute(stmt)).scalars().all())
