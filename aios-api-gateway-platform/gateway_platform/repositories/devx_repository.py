from __future__ import annotations

from sqlalchemy import select

from gateway_platform.models.devx import SdkGenJobModel, TestConsoleRequestModel
from gateway_platform.repositories.base import SQLAlchemyRepository


class SdkGenJobRepository(SQLAlchemyRepository[SdkGenJobModel]):
    model = SdkGenJobModel

    async def list_for_tenant(self, tenant_id: str) -> list[SdkGenJobModel]:
        stmt = select(SdkGenJobModel).where(SdkGenJobModel.tenant_id == tenant_id, SdkGenJobModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())


class TestConsoleRequestRepository(SQLAlchemyRepository[TestConsoleRequestModel]):
    model = TestConsoleRequestModel

    async def list_for_route(self, tenant_id: str, route_id: str, *, limit: int = 100) -> list[TestConsoleRequestModel]:
        stmt = select(TestConsoleRequestModel).where(
            TestConsoleRequestModel.tenant_id == tenant_id, TestConsoleRequestModel.route_id == route_id,
        ).order_by(TestConsoleRequestModel.executed_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
