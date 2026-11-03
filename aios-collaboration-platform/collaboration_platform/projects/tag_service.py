"""TagService: workspace-scoped tags applied to assets many-to-many."""
from __future__ import annotations

from collaboration_platform.core.exceptions import ConflictError, NotFoundError
from collaboration_platform.models.workspace import AssetTagModel, TagModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class TagService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_tag(self, workspace_id: str, *, name: str, color: str | None = None) -> TagModel:
        await self.repos.workspaces.get_or_404(workspace_id)
        if await self.repos.tags.get_by_name(workspace_id, name) is not None:
            raise ConflictError(f"tag '{name}' already exists in workspace '{workspace_id}'")
        return await self.repos.tags.add(TagModel(workspace_id=workspace_id, name=name, color=color))

    async def tag_asset(self, asset_id: str, tag_id: str) -> AssetTagModel:
        await self.repos.assets.get_or_404(asset_id)
        await self.repos.tags.get_or_404(tag_id)
        existing = await self.repos.asset_tags.get_link(asset_id, tag_id)
        if existing is not None:
            raise ConflictError(f"asset '{asset_id}' is already tagged '{tag_id}'")
        return await self.repos.asset_tags.add(AssetTagModel(asset_id=asset_id, tag_id=tag_id))

    async def untag_asset(self, asset_id: str, tag_id: str) -> None:
        link = await self.repos.asset_tags.get_link(asset_id, tag_id)
        if link is None:
            raise NotFoundError(f"asset '{asset_id}' is not tagged '{tag_id}'")
        await self.repos.asset_tags.delete(link, hard=True)

    async def list_tags_for_asset(self, asset_id: str) -> list[AssetTagModel]:
        return await self.repos.asset_tags.list_for_asset(asset_id)

    async def list_for_workspace(self, workspace_id: str) -> list[TagModel]:
        return await self.repos.tags.list_for_workspace(workspace_id)
