from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from perf_platform.models.cache import CacheEntryModel, CacheStatModel
from perf_platform.repositories.base import SQLAlchemyRepository
from perf_platform.clock import utc_now


class CacheEntryRepository(SQLAlchemyRepository[CacheEntryModel]):
    model = CacheEntryModel

    async def get_by_key(self, tenant_id: str, layer: str, key: str) -> CacheEntryModel | None:
        stmt = select(CacheEntryModel).where(
            CacheEntryModel.tenant_id == tenant_id, CacheEntryModel.layer == layer, CacheEntryModel.key == key,
            CacheEntryModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_layer(self, tenant_id: str, layer: str, *, limit: int = 100) -> list[CacheEntryModel]:
        stmt = select(CacheEntryModel).where(
            CacheEntryModel.tenant_id == tenant_id, CacheEntryModel.layer == layer, CacheEntryModel.is_deleted.is_(False),
        ).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_expired(self, tenant_id: str, *, as_of: datetime | None = None) -> list[CacheEntryModel]:
        as_of = as_of or utc_now()
        stmt = select(CacheEntryModel).where(
            CacheEntryModel.tenant_id == tenant_id, CacheEntryModel.is_deleted.is_(False),
            CacheEntryModel.ttl_expires_at.is_not(None), CacheEntryModel.ttl_expires_at < as_of,
        )
        return list((await self.session.execute(stmt)).scalars().all())


class CacheStatRepository(SQLAlchemyRepository[CacheStatModel]):
    model = CacheStatModel

    async def get_for_layer(self, tenant_id: str, layer: str) -> CacheStatModel | None:
        stmt = select(CacheStatModel).where(CacheStatModel.tenant_id == tenant_id, CacheStatModel.layer == layer)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[CacheStatModel]:
        stmt = select(CacheStatModel).where(CacheStatModel.tenant_id == tenant_id)
        return list((await self.session.execute(stmt)).scalars().all())
