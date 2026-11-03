from __future__ import annotations

from sqlalchemy import select

from developer_platform.models.plugins import (
    PluginDependencyModel,
    PluginMarketplaceListingModel,
    PluginModel,
    PluginVersionModel,
)
from developer_platform.repositories.base import SQLAlchemyRepository


class PluginRepository(SQLAlchemyRepository[PluginModel]):
    model = PluginModel

    async def get_by_name(self, tenant_id: str, name: str) -> PluginModel | None:
        stmt = select(PluginModel).where(PluginModel.tenant_id == tenant_id, PluginModel.name == name, PluginModel.is_deleted.is_(False))
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[PluginModel]:
        stmt = select(PluginModel).where(PluginModel.tenant_id == tenant_id, PluginModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_category(self, tenant_id: str, category: str) -> list[PluginModel]:
        stmt = select(PluginModel).where(
            PluginModel.tenant_id == tenant_id, PluginModel.category == category, PluginModel.is_deleted.is_(False)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class PluginVersionRepository(SQLAlchemyRepository[PluginVersionModel]):
    model = PluginVersionModel

    async def list_for_plugin(self, tenant_id: str, plugin_id: str) -> list[PluginVersionModel]:
        stmt = select(PluginVersionModel).where(
            PluginVersionModel.tenant_id == tenant_id, PluginVersionModel.plugin_id == plugin_id
        ).order_by(PluginVersionModel.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_version(self, tenant_id: str, plugin_id: str, version: str) -> PluginVersionModel | None:
        stmt = select(PluginVersionModel).where(
            PluginVersionModel.tenant_id == tenant_id, PluginVersionModel.plugin_id == plugin_id, PluginVersionModel.version == version
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_status(self, tenant_id: str, plugin_id: str, status: str) -> list[PluginVersionModel]:
        stmt = select(PluginVersionModel).where(
            PluginVersionModel.tenant_id == tenant_id, PluginVersionModel.plugin_id == plugin_id, PluginVersionModel.status == status
        )
        return list((await self.session.execute(stmt)).scalars().all())


class PluginDependencyRepository(SQLAlchemyRepository[PluginDependencyModel]):
    model = PluginDependencyModel

    async def list_for_version(self, tenant_id: str, plugin_version_id: str) -> list[PluginDependencyModel]:
        stmt = select(PluginDependencyModel).where(
            PluginDependencyModel.tenant_id == tenant_id, PluginDependencyModel.plugin_version_id == plugin_version_id
        )
        return list((await self.session.execute(stmt)).scalars().all())


class PluginMarketplaceListingRepository(SQLAlchemyRepository[PluginMarketplaceListingModel]):
    model = PluginMarketplaceListingModel

    async def get_for_plugin(self, tenant_id: str, plugin_id: str) -> PluginMarketplaceListingModel | None:
        stmt = select(PluginMarketplaceListingModel).where(
            PluginMarketplaceListingModel.tenant_id == tenant_id, PluginMarketplaceListingModel.plugin_id == plugin_id
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_listed(self, tenant_id: str) -> list[PluginMarketplaceListingModel]:
        stmt = select(PluginMarketplaceListingModel).where(
            PluginMarketplaceListingModel.tenant_id == tenant_id, PluginMarketplaceListingModel.is_listed.is_(True)
        )
        return list((await self.session.execute(stmt)).scalars().all())
