from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select

from developer_platform.models.api_platform import ApiKeyModel, ApiUsageRecordModel, ApiVersionModel
from developer_platform.repositories.base import SQLAlchemyRepository


class ApiKeyRepository(SQLAlchemyRepository[ApiKeyModel]):
    model = ApiKeyModel

    async def get_by_key_hash(self, key_hash: str) -> ApiKeyModel | None:
        stmt = select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash, ApiKeyModel.is_deleted.is_(False))
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[ApiKeyModel]:
        stmt = select(ApiKeyModel).where(ApiKeyModel.tenant_id == tenant_id, ApiKeyModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())


class ApiUsageRecordRepository(SQLAlchemyRepository[ApiUsageRecordModel]):
    model = ApiUsageRecordModel

    async def list_recent(self, tenant_id: str, *, api_key_id: str | None = None, limit: int = 200) -> list[ApiUsageRecordModel]:
        stmt = select(ApiUsageRecordModel).where(ApiUsageRecordModel.tenant_id == tenant_id)
        if api_key_id:
            stmt = stmt.where(ApiUsageRecordModel.api_key_id == api_key_id)
        stmt = stmt.order_by(ApiUsageRecordModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_since(self, tenant_id: str, api_key_id: str, since: datetime) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(ApiUsageRecordModel).where(
            ApiUsageRecordModel.tenant_id == tenant_id, ApiUsageRecordModel.api_key_id == api_key_id,
            ApiUsageRecordModel.recorded_at >= since,
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        stmt = delete(ApiUsageRecordModel).where(
            ApiUsageRecordModel.tenant_id == tenant_id, ApiUsageRecordModel.recorded_at < cutoff
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0


class ApiVersionRepository(SQLAlchemyRepository[ApiVersionModel]):
    model = ApiVersionModel

    async def get_by_version(self, version: str) -> ApiVersionModel | None:
        stmt = select(ApiVersionModel).where(ApiVersionModel.version == version)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_all(self) -> list[ApiVersionModel]:
        stmt = select(ApiVersionModel)
        return list((await self.session.execute(stmt)).scalars().all())
