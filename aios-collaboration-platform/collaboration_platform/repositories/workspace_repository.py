from __future__ import annotations

from sqlalchemy import select

from collaboration_platform.domain.enums import WorkspaceStatus
from collaboration_platform.models.workspace import (
    AssetTagModel,
    CollectionItemModel,
    CollectionModel,
    FavoriteModel,
    FolderModel,
    ProjectModel,
    TagModel,
    WorkspaceMemberModel,
    WorkspaceModel,
    WorkspaceTemplateModel,
)
from collaboration_platform.repositories.base import SQLAlchemyRepository


class WorkspaceTemplateRepository(SQLAlchemyRepository[WorkspaceTemplateModel]):
    model = WorkspaceTemplateModel

    async def list_builtin(self) -> list[WorkspaceTemplateModel]:
        stmt = select(WorkspaceTemplateModel).where(WorkspaceTemplateModel.is_builtin.is_(True))
        return list((await self.session.execute(stmt)).scalars().all())


class WorkspaceRepository(SQLAlchemyRepository[WorkspaceModel]):
    model = WorkspaceModel

    async def get_by_slug(self, slug: str) -> WorkspaceModel | None:
        stmt = select(WorkspaceModel).where(WorkspaceModel.slug == slug)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_owner(self, owner_id: str, *, status: str | None = None) -> list[WorkspaceModel]:
        stmt = select(WorkspaceModel).where(WorkspaceModel.owner_id == owner_id)
        if status:
            stmt = stmt.where(WorkspaceModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_organization(self, organization_id: str) -> list[WorkspaceModel]:
        stmt = select(WorkspaceModel).where(WorkspaceModel.organization_id == organization_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_active(self) -> list[WorkspaceModel]:
        stmt = select(WorkspaceModel).where(WorkspaceModel.status == WorkspaceStatus.ACTIVE.value)
        return list((await self.session.execute(stmt)).scalars().all())


class WorkspaceMemberRepository(SQLAlchemyRepository[WorkspaceMemberModel]):
    model = WorkspaceMemberModel

    async def get_for_workspace_and_user(self, workspace_id: str, user_id: str) -> WorkspaceMemberModel | None:
        stmt = select(WorkspaceMemberModel).where(
            WorkspaceMemberModel.workspace_id == workspace_id, WorkspaceMemberModel.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_workspace(self, workspace_id: str) -> list[WorkspaceMemberModel]:
        stmt = select(WorkspaceMemberModel).where(WorkspaceMemberModel.workspace_id == workspace_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_user(self, user_id: str) -> list[WorkspaceMemberModel]:
        stmt = select(WorkspaceMemberModel).where(WorkspaceMemberModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())


class ProjectRepository(SQLAlchemyRepository[ProjectModel]):
    model = ProjectModel

    async def list_for_workspace(self, workspace_id: str, *, status: str | None = None) -> list[ProjectModel]:
        stmt = select(ProjectModel).where(ProjectModel.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(ProjectModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())


class FolderRepository(SQLAlchemyRepository[FolderModel]):
    model = FolderModel

    async def list_for_workspace(self, workspace_id: str) -> list[FolderModel]:
        stmt = select(FolderModel).where(FolderModel.workspace_id == workspace_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_children(self, parent_folder_id: str) -> list[FolderModel]:
        stmt = select(FolderModel).where(FolderModel.parent_folder_id == parent_folder_id)
        return list((await self.session.execute(stmt)).scalars().all())


class CollectionRepository(SQLAlchemyRepository[CollectionModel]):
    model = CollectionModel

    async def list_for_workspace(self, workspace_id: str) -> list[CollectionModel]:
        stmt = select(CollectionModel).where(CollectionModel.workspace_id == workspace_id)
        return list((await self.session.execute(stmt)).scalars().all())


class CollectionItemRepository(SQLAlchemyRepository[CollectionItemModel]):
    model = CollectionItemModel

    async def list_for_collection(self, collection_id: str) -> list[CollectionItemModel]:
        stmt = select(CollectionItemModel).where(CollectionItemModel.collection_id == collection_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_collection_and_asset(self, collection_id: str, asset_id: str) -> CollectionItemModel | None:
        stmt = select(CollectionItemModel).where(
            CollectionItemModel.collection_id == collection_id, CollectionItemModel.asset_id == asset_id
        )
        return (await self.session.execute(stmt)).scalars().first()


class TagRepository(SQLAlchemyRepository[TagModel]):
    model = TagModel

    async def list_for_workspace(self, workspace_id: str) -> list[TagModel]:
        stmt = select(TagModel).where(TagModel.workspace_id == workspace_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_name(self, workspace_id: str, name: str) -> TagModel | None:
        stmt = select(TagModel).where(TagModel.workspace_id == workspace_id, TagModel.name == name)
        return (await self.session.execute(stmt)).scalars().first()


class AssetTagRepository(SQLAlchemyRepository[AssetTagModel]):
    model = AssetTagModel

    async def list_for_asset(self, asset_id: str) -> list[AssetTagModel]:
        stmt = select(AssetTagModel).where(AssetTagModel.asset_id == asset_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_tag(self, tag_id: str) -> list[AssetTagModel]:
        stmt = select(AssetTagModel).where(AssetTagModel.tag_id == tag_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_link(self, asset_id: str, tag_id: str) -> AssetTagModel | None:
        stmt = select(AssetTagModel).where(AssetTagModel.asset_id == asset_id, AssetTagModel.tag_id == tag_id)
        return (await self.session.execute(stmt)).scalars().first()


class FavoriteRepository(SQLAlchemyRepository[FavoriteModel]):
    model = FavoriteModel

    async def list_for_user(self, user_id: str) -> list[FavoriteModel]:
        stmt = select(FavoriteModel).where(FavoriteModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_user_and_asset(self, user_id: str, asset_id: str) -> FavoriteModel | None:
        stmt = select(FavoriteModel).where(FavoriteModel.user_id == user_id, FavoriteModel.asset_id == asset_id)
        return (await self.session.execute(stmt)).scalars().first()
