from __future__ import annotations

from sqlalchemy import func, or_, select

from prompt_platform.models.prompt import (
    PromptCategoryModel,
    PromptFavoriteModel,
    PromptModel,
    PromptTagLinkModel,
    PromptTagModel,
)
from prompt_platform.repositories.base import SQLAlchemyRepository


class PromptRepository(SQLAlchemyRepository[PromptModel]):
    model = PromptModel

    async def get_by_slug(self, project_id: str, slug: str) -> PromptModel | None:
        stmt = select(PromptModel).where(
            PromptModel.project_id == project_id, PromptModel.slug == slug, PromptModel.is_deleted.is_(False)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_workspace(self, workspace_id: str, *, limit: int = 100, offset: int = 0) -> list[PromptModel]:
        return await self.list(filters={"workspace_id": workspace_id}, limit=limit, offset=offset)

    async def search(self, workspace_id: str, query: str, *, limit: int = 50) -> list[PromptModel]:
        like = f"%{query.lower()}%"
        stmt = (
            select(PromptModel)
            .where(
                PromptModel.workspace_id == workspace_id,
                PromptModel.is_deleted.is_(False),
                or_(func.lower(PromptModel.name).like(like), func.lower(PromptModel.description).like(like)),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class PromptCategoryRepository(SQLAlchemyRepository[PromptCategoryModel]):
    model = PromptCategoryModel


class PromptTagRepository(SQLAlchemyRepository[PromptTagModel]):
    model = PromptTagModel

    async def get_by_name(self, name: str) -> PromptTagModel | None:
        stmt = select(PromptTagModel).where(PromptTagModel.name == name)
        return (await self.session.execute(stmt)).scalars().first()

    async def link(self, prompt_id: str, tag_id: str) -> None:
        self.session.add(PromptTagLinkModel(prompt_id=prompt_id, tag_id=tag_id))
        await self.session.flush()

    async def unlink(self, prompt_id: str, tag_id: str) -> None:
        stmt = select(PromptTagLinkModel).where(
            PromptTagLinkModel.prompt_id == prompt_id, PromptTagLinkModel.tag_id == tag_id
        )
        link = (await self.session.execute(stmt)).scalars().first()
        if link is not None:
            await self.session.delete(link)
            await self.session.flush()

    async def tags_for_prompt(self, prompt_id: str) -> list[PromptTagModel]:
        stmt = select(PromptTagModel).join(PromptTagLinkModel, PromptTagLinkModel.tag_id == PromptTagModel.id).where(
            PromptTagLinkModel.prompt_id == prompt_id
        )
        return list((await self.session.execute(stmt)).scalars().all())


class PromptFavoriteRepository(SQLAlchemyRepository[PromptFavoriteModel]):
    model = PromptFavoriteModel

    async def is_favorite(self, user_id: str, prompt_id: str) -> bool:
        stmt = select(PromptFavoriteModel).where(
            PromptFavoriteModel.user_id == user_id, PromptFavoriteModel.prompt_id == prompt_id
        )
        return (await self.session.execute(stmt)).scalars().first() is not None

    async def list_for_user(self, user_id: str) -> list[PromptFavoriteModel]:
        stmt = select(PromptFavoriteModel).where(PromptFavoriteModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def remove(self, user_id: str, prompt_id: str) -> None:
        stmt = select(PromptFavoriteModel).where(
            PromptFavoriteModel.user_id == user_id, PromptFavoriteModel.prompt_id == prompt_id
        )
        fav = (await self.session.execute(stmt)).scalars().first()
        if fav is not None:
            await self.session.delete(fav)
            await self.session.flush()
