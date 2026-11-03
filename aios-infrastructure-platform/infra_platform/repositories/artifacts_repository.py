from __future__ import annotations

from sqlalchemy import func, select

from infra_platform.models.artifacts import ArtifactModel, ArtifactVersionModel
from infra_platform.repositories.base import SQLAlchemyRepository


class ArtifactRepository(SQLAlchemyRepository[ArtifactModel]):
    model = ArtifactModel

    async def get_by_name_type(self, tenant_id: str, name: str, artifact_type: str) -> ArtifactModel | None:
        stmt = select(ArtifactModel).where(
            ArtifactModel.tenant_id == tenant_id, ArtifactModel.name == name, ArtifactModel.artifact_type == artifact_type, ArtifactModel.is_deleted.is_(False)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_type(self, tenant_id: str, artifact_type: str) -> list[ArtifactModel]:
        stmt = select(ArtifactModel).where(ArtifactModel.tenant_id == tenant_id, ArtifactModel.artifact_type == artifact_type, ArtifactModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())


class ArtifactVersionRepository(SQLAlchemyRepository[ArtifactVersionModel]):
    model = ArtifactVersionModel

    async def list_for_artifact(self, tenant_id: str, artifact_id: str) -> list[ArtifactVersionModel]:
        stmt = select(ArtifactVersionModel).where(
            ArtifactVersionModel.tenant_id == tenant_id, ArtifactVersionModel.artifact_id == artifact_id
        ).order_by(ArtifactVersionModel.version_number.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_latest_version_number(self, tenant_id: str, artifact_id: str) -> int:
        stmt = select(func.max(ArtifactVersionModel.version_number)).where(
            ArtifactVersionModel.tenant_id == tenant_id, ArtifactVersionModel.artifact_id == artifact_id
        )
        result = (await self.session.execute(stmt)).scalar_one_or_none()
        return result or 0
