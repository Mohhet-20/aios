from __future__ import annotations

from sqlalchemy import select

from release_platform.models.security import ArtifactSignatureModel, ReleaseApprovalModel, SbomModel
from release_platform.repositories.base import SQLAlchemyRepository


class SbomRepository(SQLAlchemyRepository[SbomModel]):
    model = SbomModel

    async def list_for_artifact(self, tenant_id: str, artifact_id: str) -> list[SbomModel]:
        stmt = select(SbomModel).where(SbomModel.tenant_id == tenant_id, SbomModel.artifact_id == artifact_id)
        return list((await self.session.execute(stmt)).scalars().all())


class ArtifactSignatureRepository(SQLAlchemyRepository[ArtifactSignatureModel]):
    model = ArtifactSignatureModel

    async def list_for_artifact(self, tenant_id: str, artifact_id: str) -> list[ArtifactSignatureModel]:
        stmt = select(ArtifactSignatureModel).where(
            ArtifactSignatureModel.tenant_id == tenant_id, ArtifactSignatureModel.artifact_id == artifact_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ReleaseApprovalRepository(SQLAlchemyRepository[ReleaseApprovalModel]):
    model = ReleaseApprovalModel

    async def list_for_release(self, tenant_id: str, release_id: str) -> list[ReleaseApprovalModel]:
        stmt = select(ReleaseApprovalModel).where(
            ReleaseApprovalModel.tenant_id == tenant_id, ReleaseApprovalModel.release_id == release_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())
