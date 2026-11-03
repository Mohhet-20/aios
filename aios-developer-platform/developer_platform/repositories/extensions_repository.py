from __future__ import annotations

from sqlalchemy import select

from developer_platform.models.extensions import ExtensionPointModel, ExtensionRegistrationModel
from developer_platform.repositories.base import SQLAlchemyRepository


class ExtensionPointRepository(SQLAlchemyRepository[ExtensionPointModel]):
    model = ExtensionPointModel

    async def get_by_name(self, tenant_id: str, category: str, name: str) -> ExtensionPointModel | None:
        stmt = select(ExtensionPointModel).where(
            ExtensionPointModel.tenant_id == tenant_id, ExtensionPointModel.category == category, ExtensionPointModel.name == name
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_category(self, tenant_id: str, category: str) -> list[ExtensionPointModel]:
        stmt = select(ExtensionPointModel).where(
            ExtensionPointModel.tenant_id == tenant_id, ExtensionPointModel.category == category
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ExtensionRegistrationRepository(SQLAlchemyRepository[ExtensionRegistrationModel]):
    model = ExtensionRegistrationModel

    async def list_for_point(self, tenant_id: str, extension_point_id: str) -> list[ExtensionRegistrationModel]:
        stmt = select(ExtensionRegistrationModel).where(
            ExtensionRegistrationModel.tenant_id == tenant_id, ExtensionRegistrationModel.extension_point_id == extension_point_id
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_plugin(self, tenant_id: str, plugin_id: str) -> list[ExtensionRegistrationModel]:
        stmt = select(ExtensionRegistrationModel).where(
            ExtensionRegistrationModel.tenant_id == tenant_id, ExtensionRegistrationModel.plugin_id == plugin_id
        )
        return list((await self.session.execute(stmt)).scalars().all())
