from __future__ import annotations

from sqlalchemy import select

from gateway_platform.models.protocols import ProtocolTranslationConfigModel
from gateway_platform.repositories.base import SQLAlchemyRepository


class ProtocolTranslationConfigRepository(SQLAlchemyRepository[ProtocolTranslationConfigModel]):
    model = ProtocolTranslationConfigModel

    async def list_for_route(self, tenant_id: str, route_id: str) -> list[ProtocolTranslationConfigModel]:
        stmt = select(ProtocolTranslationConfigModel).where(
            ProtocolTranslationConfigModel.tenant_id == tenant_id, ProtocolTranslationConfigModel.route_id == route_id,
            ProtocolTranslationConfigModel.is_deleted.is_(False),
        )
        return list((await self.session.execute(stmt)).scalars().all())
