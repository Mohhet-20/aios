from __future__ import annotations

from sqlalchemy import or_, select

from collaboration_platform.domain.enums import AssetStatus
from collaboration_platform.models.asset import CollaborationAssetModel
from collaboration_platform.repositories.base import SQLAlchemyRepository


class CollaborationAssetRepository(SQLAlchemyRepository[CollaborationAssetModel]):
    model = CollaborationAssetModel

    async def get_by_external_ref(self, asset_type: str, external_ref_id: str) -> CollaborationAssetModel | None:
        stmt = select(CollaborationAssetModel).where(
            CollaborationAssetModel.asset_type == asset_type,
            CollaborationAssetModel.external_ref_id == external_ref_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_workspace(
        self, workspace_id: str, *, asset_type: str | None = None, status: str | None = None
    ) -> list[CollaborationAssetModel]:
        stmt = select(CollaborationAssetModel).where(CollaborationAssetModel.workspace_id == workspace_id)
        if asset_type:
            stmt = stmt.where(CollaborationAssetModel.asset_type == asset_type)
        if status:
            stmt = stmt.where(CollaborationAssetModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_project(self, project_id: str) -> list[CollaborationAssetModel]:
        stmt = select(CollaborationAssetModel).where(CollaborationAssetModel.project_id == project_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_owner(self, owner_id: str) -> list[CollaborationAssetModel]:
        stmt = select(CollaborationAssetModel).where(CollaborationAssetModel.owner_id == owner_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_active(self, workspace_id: str) -> list[CollaborationAssetModel]:
        stmt = select(CollaborationAssetModel).where(
            CollaborationAssetModel.workspace_id == workspace_id,
            CollaborationAssetModel.status == AssetStatus.ACTIVE.value,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_lexical(
        self, query: str, *, workspace_id: str | None = None, asset_type: str | None = None, limit: int = 50
    ) -> list[CollaborationAssetModel]:
        """Case-insensitive substring match over name/description —
        deliberately named `search_lexical` (not `search`) so callers
        can't mistake this for semantic/embedding-based search, which
        this platform doesn't implement itself (see
        `search/search_service.py`'s `SemanticSearchProvider`)."""
        like_pattern = f"%{query.lower()}%"
        stmt = select(CollaborationAssetModel).where(
            CollaborationAssetModel.status != "deleted",
            or_(
                CollaborationAssetModel.name.ilike(like_pattern),
                CollaborationAssetModel.description.ilike(like_pattern),
            ),
        )
        if workspace_id:
            stmt = stmt.where(CollaborationAssetModel.workspace_id == workspace_id)
        if asset_type:
            stmt = stmt.where(CollaborationAssetModel.asset_type == asset_type)
        stmt = stmt.limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
