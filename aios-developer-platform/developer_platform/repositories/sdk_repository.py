from __future__ import annotations

from sqlalchemy import select

from developer_platform.models.sdk import SdkCompatibilityEntryModel
from developer_platform.repositories.base import SQLAlchemyRepository


class SdkCompatibilityEntryRepository(SQLAlchemyRepository[SdkCompatibilityEntryModel]):
    model = SdkCompatibilityEntryModel

    async def list_for_language(self, tenant_id: str, language: str) -> list[SdkCompatibilityEntryModel]:
        stmt = select(SdkCompatibilityEntryModel).where(
            SdkCompatibilityEntryModel.tenant_id == tenant_id, SdkCompatibilityEntryModel.language == language
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_entry(self, tenant_id: str, language: str, sdk_major_version: int) -> SdkCompatibilityEntryModel | None:
        stmt = select(SdkCompatibilityEntryModel).where(
            SdkCompatibilityEntryModel.tenant_id == tenant_id, SdkCompatibilityEntryModel.language == language,
            SdkCompatibilityEntryModel.sdk_major_version == sdk_major_version,
        )
        return (await self.session.execute(stmt)).scalars().first()
