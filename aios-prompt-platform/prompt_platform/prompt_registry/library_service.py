"""Prompt Library: search/filter/sort, favorites, recently-used/most-used,
collections, categories, and tags. This is the "browse and discover"
surface — CRUD on a single prompt's content lives in prompt_editor/ and
prompt_engine/, not here.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import select

from prompt_platform.core.exceptions import ValidationError
from prompt_platform.core.pagination import Page, PaginationParams
from prompt_platform.domain.enums import PromptStatus
from prompt_platform.models.prompt import PromptModel
from prompt_platform.repositories.registry import RepositoryRegistry


class PromptLibraryService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    # -- search / filter / sort --------------------------------------------

    async def search(
        self,
        workspace_id: str,
        *,
        query: str | None = None,
        category_id: str | None = None,
        visibility: str | None = None,
        status: str | None = None,
        owner_id: str | None = None,
        sort: str = "updated_at",
        pagination: PaginationParams | None = None,
    ) -> Page[PromptModel]:
        pagination = pagination or PaginationParams()
        filters: dict[str, Any] = {"workspace_id": workspace_id}
        for key, value in (("category_id", category_id), ("visibility", visibility), ("status", status), ("owner_id", owner_id)):
            if value is not None:
                filters[key] = value

        if query:
            matches = await self.repos.prompts.search(workspace_id, query)
            matches = [m for m in matches if all(getattr(m, k) == v for k, v in filters.items() if k != "workspace_id")]
            total = len(matches)
            sorted_items = self._sort(matches, sort)
            page_items = sorted_items[pagination.offset : pagination.offset + pagination.page_size]
            return Page(items=page_items, total=total, page=pagination.page, page_size=pagination.page_size)

        page = await self.repos.prompts.paginated_list(pagination, filters=filters)
        page.items = self._sort(page.items, sort)
        return page

    def _sort(self, items: list[PromptModel], sort: str) -> list[PromptModel]:
        if sort == "name":
            return sorted(items, key=lambda p: p.name.lower())
        if sort == "created_at":
            return sorted(items, key=lambda p: p.created_at, reverse=True)
        return sorted(items, key=lambda p: p.updated_at, reverse=True)  # default: updated_at

    # -- favorites ------------------------------------------------------------

    async def add_favorite(self, user_id: str, prompt_id: str) -> None:
        await self.repos.prompts.get_or_404(prompt_id)
        if not await self.repos.favorites.is_favorite(user_id, prompt_id):
            from prompt_platform.models.prompt import PromptFavoriteModel

            await self.repos.favorites.add(PromptFavoriteModel(user_id=user_id, prompt_id=prompt_id))

    async def remove_favorite(self, user_id: str, prompt_id: str) -> None:
        await self.repos.favorites.remove(user_id, prompt_id)

    async def list_favorites(self, user_id: str) -> list[PromptModel]:
        favorites = await self.repos.favorites.list_for_user(user_id)
        return await self.repos.prompts.get_many([fav.prompt_id for fav in favorites])

    # -- recently used / most used (derived from execution logs) --------------

    async def list_recently_used(self, workspace_id: str, *, limit: int = 10) -> list[PromptModel]:
        stmt = select(PromptModel).where(PromptModel.workspace_id == workspace_id, PromptModel.is_deleted.is_(False))
        all_prompts = {p.id: p for p in (await self.repos.session.execute(stmt)).scalars().all()}

        seen: list[str] = []
        for prompt_id in all_prompts:
            logs = await self.repos.execution_logs.list_for_prompt(prompt_id, limit=1)
            if logs:
                seen.append((prompt_id, logs[0].created_at))
        seen.sort(key=lambda t: t[1], reverse=True)
        return [all_prompts[pid] for pid, _ in seen[:limit]]

    async def list_most_used(self, workspace_id: str, *, limit: int = 10) -> list[tuple[PromptModel, int]]:
        stmt = select(PromptModel).where(PromptModel.workspace_id == workspace_id, PromptModel.is_deleted.is_(False))
        prompts = list((await self.repos.session.execute(stmt)).scalars().all())
        counts: Counter[str] = Counter()
        for prompt in prompts:
            logs = await self.repos.execution_logs.list_for_prompt(prompt.id, limit=10_000)
            counts[prompt.id] = len(logs)
        ranked = sorted(prompts, key=lambda p: counts[p.id], reverse=True)
        return [(p, counts[p.id]) for p in ranked[:limit]]

    # -- archive ---------------------------------------------------------------

    async def archive(self, prompt_id: str) -> PromptModel:
        prompt = await self.repos.prompts.get_or_404(prompt_id)
        prompt.status = PromptStatus.ARCHIVED.value
        return await self.repos.prompts.update(prompt)

    async def unarchive(self, prompt_id: str) -> PromptModel:
        prompt = await self.repos.prompts.get_or_404(prompt_id)
        prompt.status = PromptStatus.ACTIVE.value
        return await self.repos.prompts.update(prompt)

    # -- categories --------------------------------------------------------------

    async def create_category(self, name: str, slug: str, description: str | None = None):
        from prompt_platform.models.prompt import PromptCategoryModel

        return await self.repos.categories.add(PromptCategoryModel(name=name, slug=slug, description=description))

    async def list_categories(self) -> list:
        return await self.repos.categories.list(limit=500)

    # -- tags --------------------------------------------------------------------

    async def tag_prompt(self, prompt_id: str, tag_name: str) -> None:
        from prompt_platform.models.prompt import PromptTagModel

        prompt = await self.repos.prompts.get_or_404(prompt_id)
        tag = await self.repos.tags.get_by_name(tag_name)
        if tag is None:
            tag = await self.repos.tags.add(PromptTagModel(name=tag_name, slug=tag_name.lower().replace(" ", "-")))
        await self.repos.tags.link(prompt_id, tag.id)
        if tag_name not in (prompt.tags_cache or []):
            prompt.tags_cache = [*(prompt.tags_cache or []), tag_name]
            await self.repos.prompts.update(prompt)

    async def untag_prompt(self, prompt_id: str, tag_name: str) -> None:
        prompt = await self.repos.prompts.get_or_404(prompt_id)
        tag = await self.repos.tags.get_by_name(tag_name)
        if tag is not None:
            await self.repos.tags.unlink(prompt_id, tag.id)
        prompt.tags_cache = [t for t in (prompt.tags_cache or []) if t != tag_name]
        await self.repos.prompts.update(prompt)

    # -- collections --------------------------------------------------------------

    async def create_collection(self, workspace_id: str, name: str, owner_id: str, *, description: str | None = None, is_shared: bool = False):
        from prompt_platform.models.collection import PromptCollectionModel

        return await self.repos.collections.add(
            PromptCollectionModel(workspace_id=workspace_id, name=name, owner_id=owner_id, description=description, is_shared=is_shared)
        )

    async def add_to_collection(self, collection_id: str, prompt_id: str) -> None:
        await self.repos.collections.get_or_404(collection_id)
        await self.repos.prompts.get_or_404(prompt_id)
        if await self.repos.collection_items.is_member(collection_id, prompt_id):
            raise ValidationError(f"prompt {prompt_id} is already in collection {collection_id}")
        from prompt_platform.models.collection import PromptCollectionItemModel

        await self.repos.collection_items.add(PromptCollectionItemModel(collection_id=collection_id, prompt_id=prompt_id))

    async def remove_from_collection(self, collection_id: str, prompt_id: str) -> None:
        await self.repos.collection_items.remove(collection_id, prompt_id)

    async def list_collection_prompts(self, collection_id: str) -> list[PromptModel]:
        prompt_ids = await self.repos.collection_items.list_prompts_in_collection(collection_id)
        return await self.repos.prompts.get_many(prompt_ids)

    async def list_collections(self, workspace_id: str) -> list:
        return await self.repos.collections.list_for_workspace(workspace_id)
