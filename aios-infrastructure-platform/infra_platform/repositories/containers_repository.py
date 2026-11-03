from __future__ import annotations

from sqlalchemy import select

from infra_platform.models.containers import ContainerImageModel, ImageScanResultModel, ImageSignatureModel
from infra_platform.repositories.base import SQLAlchemyRepository


class ContainerImageRepository(SQLAlchemyRepository[ContainerImageModel]):
    model = ContainerImageModel

    async def get_by_repo_tag(self, tenant_id: str, repository: str, tag: str) -> ContainerImageModel | None:
        stmt = select(ContainerImageModel).where(
            ContainerImageModel.tenant_id == tenant_id, ContainerImageModel.repository == repository,
            ContainerImageModel.tag == tag, ContainerImageModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_repository(self, tenant_id: str, repository: str) -> list[ContainerImageModel]:
        stmt = select(ContainerImageModel).where(
            ContainerImageModel.tenant_id == tenant_id, ContainerImageModel.repository == repository, ContainerImageModel.is_deleted.is_(False)
        ).order_by(ContainerImageModel.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())


class ImageScanResultRepository(SQLAlchemyRepository[ImageScanResultModel]):
    model = ImageScanResultModel

    async def list_for_image(self, tenant_id: str, image_id: str) -> list[ImageScanResultModel]:
        stmt = select(ImageScanResultModel).where(
            ImageScanResultModel.tenant_id == tenant_id, ImageScanResultModel.image_id == image_id
        ).order_by(ImageScanResultModel.scanned_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())


class ImageSignatureRepository(SQLAlchemyRepository[ImageSignatureModel]):
    model = ImageSignatureModel

    async def list_for_image(self, tenant_id: str, image_id: str) -> list[ImageSignatureModel]:
        stmt = select(ImageSignatureModel).where(
            ImageSignatureModel.tenant_id == tenant_id, ImageSignatureModel.image_id == image_id
        ).order_by(ImageSignatureModel.signed_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())
