from __future__ import annotations

from sqlalchemy import select, update

from collaboration_platform.models.library import LibraryAssetModel, LibraryFavoriteModel
from collaboration_platform.repositories.base import SQLAlchemyRepository


class LibraryAssetRepository(SQLAlchemyRepository[LibraryAssetModel]):
    model = LibraryAssetModel

    async def get_for_asset(self, asset_id: str) -> LibraryAssetModel | None:
        stmt = select(LibraryAssetModel).where(LibraryAssetModel.asset_id == asset_id)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_published(self, *, visibility: str | None = None, library_type: str | None = None) -> list[LibraryAssetModel]:
        stmt = select(LibraryAssetModel).where(LibraryAssetModel.unpublished_at.is_(None))
        if visibility:
            stmt = stmt.where(LibraryAssetModel.visibility == visibility)
        if library_type:
            stmt = stmt.where(LibraryAssetModel.library_type == library_type)
        return list((await self.session.execute(stmt)).scalars().all())

    async def increment_install_count(self, library_asset_id: str) -> None:
        """A single `UPDATE ... SET install_count = install_count + 1`
        rather than a read-then-write — SQLite serializes concurrent
        writers on the same row, so this is safe under concurrent
        installs without needing an application-level lock (the same
        atomic-statement principle as the Identity Platform's seat-quota
        fix, applied here to a simple counter instead of a guarded
        insert)."""
        stmt = update(LibraryAssetModel).where(LibraryAssetModel.id == library_asset_id).values(
            install_count=LibraryAssetModel.install_count + 1
        )
        await self.session.execute(stmt)
        await self.session.flush()


class LibraryFavoriteRepository(SQLAlchemyRepository[LibraryFavoriteModel]):
    model = LibraryFavoriteModel

    async def list_for_user(self, user_id: str) -> list[LibraryFavoriteModel]:
        stmt = select(LibraryFavoriteModel).where(LibraryFavoriteModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_user_and_library_asset(self, user_id: str, library_asset_id: str) -> LibraryFavoriteModel | None:
        stmt = select(LibraryFavoriteModel).where(
            LibraryFavoriteModel.user_id == user_id, LibraryFavoriteModel.library_asset_id == library_asset_id
        )
        return (await self.session.execute(stmt)).scalars().first()
