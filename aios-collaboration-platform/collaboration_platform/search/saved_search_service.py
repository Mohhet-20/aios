"""SavedSearchService: named, reusable search queries per user, capped
at `saved_search_limit_per_user`."""
from __future__ import annotations

from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.core.exceptions import NotFoundError, QuotaExceededError
from collaboration_platform.models.search import SavedSearchModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class SavedSearchService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create(self, user_id: str, *, name: str, query: dict) -> SavedSearchModel:
        existing = await self.repos.saved_searches.list_for_user(user_id)
        if len(existing) >= self.settings.saved_search_limit_per_user:
            raise QuotaExceededError(
                f"user '{user_id}' has reached the saved-search limit ({self.settings.saved_search_limit_per_user})"
            )
        return await self.repos.saved_searches.add(SavedSearchModel(user_id=user_id, name=name, query=query))

    async def delete(self, saved_search_id: str) -> None:
        saved = await self.repos.saved_searches.get(saved_search_id)
        if saved is None:
            raise NotFoundError(f"saved search '{saved_search_id}' not found")
        await self.repos.saved_searches.delete(saved, hard=True)

    async def list_for_user(self, user_id: str) -> list[SavedSearchModel]:
        return await self.repos.saved_searches.list_for_user(user_id)
