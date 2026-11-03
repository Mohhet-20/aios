from __future__ import annotations

from sqlalchemy import func, select

from infra_platform.models.model_registry import ModelApprovalModel, ModelLineageEdgeModel, ModelRegistryEntryModel, ModelVersionModel
from infra_platform.repositories.base import SQLAlchemyRepository


class ModelRegistryEntryRepository(SQLAlchemyRepository[ModelRegistryEntryModel]):
    model = ModelRegistryEntryModel

    async def get_by_name(self, tenant_id: str, name: str) -> ModelRegistryEntryModel | None:
        stmt = select(ModelRegistryEntryModel).where(
            ModelRegistryEntryModel.tenant_id == tenant_id, ModelRegistryEntryModel.name == name, ModelRegistryEntryModel.is_deleted.is_(False)
        )
        return (await self.session.execute(stmt)).scalars().first()


class ModelVersionRepository(SQLAlchemyRepository[ModelVersionModel]):
    model = ModelVersionModel

    async def list_for_model(self, tenant_id: str, model_id: str) -> list[ModelVersionModel]:
        stmt = select(ModelVersionModel).where(
            ModelVersionModel.tenant_id == tenant_id, ModelVersionModel.model_id == model_id
        ).order_by(ModelVersionModel.version_number.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_latest_version_number(self, tenant_id: str, model_id: str) -> int:
        stmt = select(func.max(ModelVersionModel.version_number)).where(
            ModelVersionModel.tenant_id == tenant_id, ModelVersionModel.model_id == model_id
        )
        result = (await self.session.execute(stmt)).scalar_one_or_none()
        return result or 0

    async def list_by_stage(self, tenant_id: str, model_id: str, stage: str) -> list[ModelVersionModel]:
        stmt = select(ModelVersionModel).where(
            ModelVersionModel.tenant_id == tenant_id, ModelVersionModel.model_id == model_id, ModelVersionModel.stage == stage
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ModelApprovalRepository(SQLAlchemyRepository[ModelApprovalModel]):
    model = ModelApprovalModel

    async def list_pending_for_version(self, tenant_id: str, model_version_id: str) -> list[ModelApprovalModel]:
        stmt = select(ModelApprovalModel).where(
            ModelApprovalModel.tenant_id == tenant_id, ModelApprovalModel.model_version_id == model_version_id, ModelApprovalModel.status == "pending"
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ModelLineageEdgeRepository(SQLAlchemyRepository[ModelLineageEdgeModel]):
    model = ModelLineageEdgeModel

    async def list_for_version(self, tenant_id: str, model_version_id: str) -> list[ModelLineageEdgeModel]:
        stmt = select(ModelLineageEdgeModel).where(
            ModelLineageEdgeModel.tenant_id == tenant_id, ModelLineageEdgeModel.model_version_id == model_version_id
        )
        return list((await self.session.execute(stmt)).scalars().all())
