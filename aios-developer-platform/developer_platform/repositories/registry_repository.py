from __future__ import annotations

from sqlalchemy import select

from developer_platform.models.registry import RegistryPackageModel, RegistryPackageVersionModel
from developer_platform.repositories.base import SQLAlchemyRepository


class RegistryPackageRepository(SQLAlchemyRepository[RegistryPackageModel]):
    model = RegistryPackageModel

    async def get_by_name_type(self, tenant_id: str, name: str, package_type: str) -> RegistryPackageModel | None:
        stmt = select(RegistryPackageModel).where(
            RegistryPackageModel.tenant_id == tenant_id, RegistryPackageModel.name == name,
            RegistryPackageModel.package_type == package_type, RegistryPackageModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_type(self, tenant_id: str, package_type: str) -> list[RegistryPackageModel]:
        stmt = select(RegistryPackageModel).where(
            RegistryPackageModel.tenant_id == tenant_id, RegistryPackageModel.package_type == package_type,
            RegistryPackageModel.is_deleted.is_(False),
        )
        return list((await self.session.execute(stmt)).scalars().all())


class RegistryPackageVersionRepository(SQLAlchemyRepository[RegistryPackageVersionModel]):
    model = RegistryPackageVersionModel

    async def list_for_package(self, tenant_id: str, package_id: str) -> list[RegistryPackageVersionModel]:
        stmt = select(RegistryPackageVersionModel).where(
            RegistryPackageVersionModel.tenant_id == tenant_id, RegistryPackageVersionModel.package_id == package_id
        ).order_by(RegistryPackageVersionModel.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_version(self, tenant_id: str, package_id: str, version: str) -> RegistryPackageVersionModel | None:
        stmt = select(RegistryPackageVersionModel).where(
            RegistryPackageVersionModel.tenant_id == tenant_id, RegistryPackageVersionModel.package_id == package_id,
            RegistryPackageVersionModel.version == version,
        )
        return (await self.session.execute(stmt)).scalars().first()
