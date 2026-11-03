from __future__ import annotations

from sqlalchemy import select

from infra_platform.models.inference import InferenceRouteModel, InferenceServiceModel
from infra_platform.repositories.base import SQLAlchemyRepository


class InferenceServiceRepository(SQLAlchemyRepository[InferenceServiceModel]):
    model = InferenceServiceModel

    async def list_for_tenant(self, tenant_id: str) -> list[InferenceServiceModel]:
        stmt = select(InferenceServiceModel).where(InferenceServiceModel.tenant_id == tenant_id, InferenceServiceModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_model_version(self, tenant_id: str, model_version_id: str) -> list[InferenceServiceModel]:
        stmt = select(InferenceServiceModel).where(
            InferenceServiceModel.tenant_id == tenant_id, InferenceServiceModel.model_version_id == model_version_id, InferenceServiceModel.is_deleted.is_(False)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class InferenceRouteRepository(SQLAlchemyRepository[InferenceRouteModel]):
    model = InferenceRouteModel

    async def list_for_service(self, tenant_id: str, inference_service_id: str) -> list[InferenceRouteModel]:
        stmt = select(InferenceRouteModel).where(
            InferenceRouteModel.tenant_id == tenant_id, InferenceRouteModel.inference_service_id == inference_service_id
        )
        return list((await self.session.execute(stmt)).scalars().all())
