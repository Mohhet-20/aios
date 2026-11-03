from __future__ import annotations

from sqlalchemy import select

from docs_platform.models.api_sdk_docs import ApiDocEntryModel, GenerationJobModel, SdkDocEntryModel
from docs_platform.repositories.base import SQLAlchemyRepository


class ApiDocEntryRepository(SQLAlchemyRepository[ApiDocEntryModel]):
    model = ApiDocEntryModel

    async def get_by_path(self, tenant_id: str, protocol_type: str, path: str, method: str | None) -> ApiDocEntryModel | None:
        stmt = select(ApiDocEntryModel).where(
            ApiDocEntryModel.tenant_id == tenant_id, ApiDocEntryModel.protocol_type == protocol_type,
            ApiDocEntryModel.path == path, ApiDocEntryModel.method == method,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, protocol_type: str | None = None) -> list[ApiDocEntryModel]:
        stmt = select(ApiDocEntryModel).where(ApiDocEntryModel.tenant_id == tenant_id)
        if protocol_type:
            stmt = stmt.where(ApiDocEntryModel.protocol_type == protocol_type)
        return list((await self.session.execute(stmt)).scalars().all())


class SdkDocEntryRepository(SQLAlchemyRepository[SdkDocEntryModel]):
    model = SdkDocEntryModel

    async def list_for_language(self, tenant_id: str, sdk_language: str) -> list[SdkDocEntryModel]:
        stmt = select(SdkDocEntryModel).where(
            SdkDocEntryModel.tenant_id == tenant_id, SdkDocEntryModel.sdk_language == sdk_language,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_tenant(self, tenant_id: str) -> list[SdkDocEntryModel]:
        stmt = select(SdkDocEntryModel).where(SdkDocEntryModel.tenant_id == tenant_id)
        return list((await self.session.execute(stmt)).scalars().all())


class GenerationJobRepository(SQLAlchemyRepository[GenerationJobModel]):
    model = GenerationJobModel

    async def list_for_tenant(self, tenant_id: str, *, job_type: str | None = None, limit: int = 100) -> list[GenerationJobModel]:
        stmt = select(GenerationJobModel).where(GenerationJobModel.tenant_id == tenant_id)
        if job_type:
            stmt = stmt.where(GenerationJobModel.job_type == job_type)
        stmt = stmt.order_by(GenerationJobModel.requested_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
