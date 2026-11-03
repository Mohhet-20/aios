from __future__ import annotations

from sqlalchemy import select

from security_platform.models.data_protection import (
    DataClassificationModel,
    DlpIncidentModel,
    DlpPolicyModel,
    PiiFindingModel,
)
from security_platform.repositories.base import SQLAlchemyRepository


class PiiFindingRepository(SQLAlchemyRepository[PiiFindingModel]):
    model = PiiFindingModel

    async def list_for_source(self, tenant_id: str, source_type: str, source_id: str) -> list[PiiFindingModel]:
        stmt = select(PiiFindingModel).where(
            PiiFindingModel.tenant_id == tenant_id,
            PiiFindingModel.source_type == source_type,
            PiiFindingModel.source_id == source_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())


class DataClassificationRepository(SQLAlchemyRepository[DataClassificationModel]):
    model = DataClassificationModel

    async def get_for_resource(self, tenant_id: str, resource_type: str, resource_id: str) -> DataClassificationModel | None:
        stmt = select(DataClassificationModel).where(
            DataClassificationModel.tenant_id == tenant_id,
            DataClassificationModel.resource_type == resource_type,
            DataClassificationModel.resource_id == resource_id,
            DataClassificationModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()


class DlpPolicyRepository(SQLAlchemyRepository[DlpPolicyModel]):
    model = DlpPolicyModel

    async def list_enabled(self, tenant_id: str) -> list[DlpPolicyModel]:
        stmt = select(DlpPolicyModel).where(
            DlpPolicyModel.tenant_id == tenant_id, DlpPolicyModel.is_deleted.is_(False), DlpPolicyModel.is_enabled.is_(True)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class DlpIncidentRepository(SQLAlchemyRepository[DlpIncidentModel]):
    model = DlpIncidentModel

    async def list_recent(self, tenant_id: str, *, limit: int = 200) -> list[DlpIncidentModel]:
        stmt = (
            select(DlpIncidentModel)
            .where(DlpIncidentModel.tenant_id == tenant_id)
            .order_by(DlpIncidentModel.detected_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())
