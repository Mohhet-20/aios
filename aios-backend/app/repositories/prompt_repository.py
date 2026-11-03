from sqlalchemy import select

from app.models.prompt import PromptModel, PromptVersionModel
from app.repositories.base import SQLAlchemyRepository


class PromptRepository(SQLAlchemyRepository[PromptModel]):
    model = PromptModel


class PromptVersionRepository(SQLAlchemyRepository[PromptVersionModel]):
    model = PromptVersionModel

    async def list_for_prompt(self, prompt_id: str) -> list[PromptVersionModel]:
        result = await self.session.execute(
            select(PromptVersionModel)
            .where(PromptVersionModel.prompt_id == prompt_id)
            .order_by(PromptVersionModel.version.desc())
        )
        return list(result.scalars().all())

    async def get_production_version(self, prompt_id: str) -> PromptVersionModel | None:
        result = await self.session.execute(
            select(PromptVersionModel).where(
                PromptVersionModel.prompt_id == prompt_id,
                PromptVersionModel.status == "production",
            )
        )
        return result.scalar_one_or_none()

    async def get_by_version_number(self, prompt_id: str, version: int) -> PromptVersionModel | None:
        result = await self.session.execute(
            select(PromptVersionModel).where(
                PromptVersionModel.prompt_id == prompt_id,
                PromptVersionModel.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def latest_version_number(self, prompt_id: str) -> int:
        versions = await self.list_for_prompt(prompt_id)
        return versions[0].version if versions else 0
