from __future__ import annotations

from sqlalchemy import select

from prompt_platform.models.collection import PromptCollectionItemModel, PromptCollectionModel
from prompt_platform.repositories.base import SQLAlchemyRepository


class PromptCollectionRepository(SQLAlchemyRepository[PromptCollectionModel]):
    model = PromptCollectionModel

    async def list_for_workspace(self, workspace_id: str) -> list[PromptCollectionModel]:
        return await self.list(filters={"workspace_id": workspace_id})


class PromptCollectionItemRepository(SQLAlchemyRepository[PromptCollectionItemModel]):
    model = PromptCollectionItemModel

    async def list_prompts_in_collection(self, collection_id: str) -> list[str]:
        stmt = select(PromptCollectionItemModel.prompt_id).where(PromptCollectionItemModel.collection_id == collection_id)
        return [row[0] for row in (await self.session.execute(stmt)).all()]

    async def is_member(self, collection_id: str, prompt_id: str) -> bool:
        stmt = select(PromptCollectionItemModel).where(
            PromptCollectionItemModel.collection_id == collection_id, PromptCollectionItemModel.prompt_id == prompt_id
        )
        return (await self.session.execute(stmt)).scalars().first() is not None

    async def remove(self, collection_id: str, prompt_id: str) -> None:
        stmt = select(PromptCollectionItemModel).where(
            PromptCollectionItemModel.collection_id == collection_id, PromptCollectionItemModel.prompt_id == prompt_id
        )
        item = (await self.session.execute(stmt)).scalars().first()
        if item is not None:
            await self.session.delete(item)
            await self.session.flush()
