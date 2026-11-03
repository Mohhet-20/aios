"""CollaborationAssetService: registers/manages the lightweight
cross-platform asset pointer every other module (comments, versions,
reviews, activity, sharing, search) attaches to. See
`models/asset.py` for why this platform stores only a pointer
(`external_ref_id`) rather than a copy of the owning platform's data."""
from __future__ import annotations

from collaboration_platform.domain.entities import CollaborationAsset
from collaboration_platform.domain.enums import AssetStatus, AssetType, AssetVisibility
from collaboration_platform.models.asset import CollaborationAssetModel
from collaboration_platform.repositories.registry import RepositoryRegistry


def _asset_to_domain(model: CollaborationAssetModel) -> CollaborationAsset:
    return CollaborationAsset(
        id=model.id, name=model.name, status=AssetStatus(model.status),
        archived_at=model.archived_at, deleted_at=model.deleted_at,
    )


def _apply_asset_domain(entity: CollaborationAsset, model: CollaborationAssetModel) -> None:
    model.status = entity.status.value
    model.archived_at = entity.archived_at
    model.deleted_at = entity.deleted_at


class CollaborationAssetService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def register_asset(
        self, *, workspace_id: str, asset_type: AssetType, external_ref_id: str, name: str, owner_id: str,
        project_id: str | None = None, folder_id: str | None = None, description: str | None = None,
        visibility: AssetVisibility = AssetVisibility.WORKSPACE,
    ) -> CollaborationAssetModel:
        await self.repos.workspaces.get_or_404(workspace_id)
        existing = await self.repos.assets.get_by_external_ref(asset_type.value, external_ref_id)
        if existing is not None:
            return existing
        return await self.repos.assets.add(CollaborationAssetModel(
            workspace_id=workspace_id, project_id=project_id, folder_id=folder_id, asset_type=asset_type.value,
            external_ref_id=external_ref_id, name=name, description=description, owner_id=owner_id,
            visibility=visibility.value,
        ))

    async def rename(self, asset_id: str, *, name: str) -> CollaborationAssetModel:
        asset = await self.repos.assets.get_or_404(asset_id)
        asset.name = name
        return await self.repos.assets.update(asset)

    async def move(self, asset_id: str, *, project_id: str | None = None, folder_id: str | None = None) -> CollaborationAssetModel:
        asset = await self.repos.assets.get_or_404(asset_id)
        asset.project_id = project_id
        asset.folder_id = folder_id
        return await self.repos.assets.update(asset)

    async def set_visibility(self, asset_id: str, visibility: AssetVisibility) -> CollaborationAssetModel:
        asset = await self.repos.assets.get_or_404(asset_id)
        asset.visibility = visibility.value
        return await self.repos.assets.update(asset)

    async def archive(self, asset_id: str) -> CollaborationAssetModel:
        asset = await self.repos.assets.get_or_404(asset_id)
        entity = _asset_to_domain(asset)
        entity.archive()
        _apply_asset_domain(entity, asset)
        return await self.repos.assets.update(asset)

    async def restore(self, asset_id: str) -> CollaborationAssetModel:
        asset = await self.repos.assets.get_or_404(asset_id)
        entity = _asset_to_domain(asset)
        entity.restore()
        _apply_asset_domain(entity, asset)
        return await self.repos.assets.update(asset)

    async def delete(self, asset_id: str) -> CollaborationAssetModel:
        asset = await self.repos.assets.get_or_404(asset_id)
        entity = _asset_to_domain(asset)
        entity.delete()
        _apply_asset_domain(entity, asset)
        return await self.repos.assets.update(asset)

    async def get(self, asset_id: str) -> CollaborationAssetModel:
        return await self.repos.assets.get_or_404(asset_id)

    async def list_for_workspace(self, workspace_id: str, *, asset_type: AssetType | None = None) -> list[CollaborationAssetModel]:
        return await self.repos.assets.list_for_workspace(workspace_id, asset_type=asset_type.value if asset_type else None)
