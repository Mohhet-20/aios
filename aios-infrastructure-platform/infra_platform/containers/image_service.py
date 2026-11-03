"""Container image registry: build -> scan -> sign -> publish
lifecycle, plus version retention pruning. A critical-severity scan
finding blocks the image from ever reaching SIGNED/PUBLISHED when
`image_scan_critical_block` is enabled — supply-chain security is a
platform-level default, not an opt-in."""
from __future__ import annotations

from infra_platform.config.settings import Settings, get_settings
from infra_platform.core.exceptions import ImageScanFailedError
from infra_platform.domain.entities import ContainerImage as ImageEntity
from infra_platform.domain.entities import _aware
from infra_platform.domain.enums import ImageStatus, ScanSeverity
from infra_platform.models.containers import ContainerImageModel, ImageScanResultModel, ImageSignatureModel
from infra_platform.repositories.registry import RepositoryRegistry


def _to_entity(model: ContainerImageModel) -> ImageEntity:
    return ImageEntity(id=model.id, status=ImageStatus(model.status))


class ImageRegistryService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_image(
        self, tenant_id: str, *, repository: str, tag: str, built_from_commit: str | None = None, created_by: str | None = None
    ) -> ContainerImageModel:
        image = ContainerImageModel(
            tenant_id=tenant_id, repository=repository, tag=tag, status=ImageStatus.BUILDING.value,
            built_from_commit=built_from_commit, created_by=created_by,
        )
        return await self.repos.container_images.add(image)

    async def start_scan(self, tenant_id: str, image_id: str) -> ContainerImageModel:
        image = await self.repos.container_images.get_or_404(image_id)
        entity = _to_entity(image)
        entity.start_scan()
        image.status = entity.status.value
        return await self.repos.container_images.update(image)

    async def record_scan_result(
        self, tenant_id: str, image_id: str, *, severity: str, finding_count: int, summary: str = ""
    ) -> ImageScanResultModel:
        result = await self.repos.image_scan_results.add(
            ImageScanResultModel(tenant_id=tenant_id, image_id=image_id, severity=severity, finding_count=finding_count, summary=summary)
        )
        if ScanSeverity(severity) == ScanSeverity.CRITICAL and self.settings.image_scan_critical_block:
            image = await self.repos.container_images.get_or_404(image_id)
            entity = _to_entity(image)
            entity.mark_scan_failed()
            image.status = entity.status.value
            await self.repos.container_images.update(image)
            raise ImageScanFailedError(f"Image '{image_id}' failed scan: {finding_count} critical finding(s)")
        return result

    async def sign_image(self, tenant_id: str, image_id: str, *, signer: str, signature: str) -> ContainerImageModel:
        await self.repos.image_signatures.add(
            ImageSignatureModel(tenant_id=tenant_id, image_id=image_id, signer=signer, signature=signature)
        )
        image = await self.repos.container_images.get_or_404(image_id)
        entity = _to_entity(image)
        entity.mark_signed()
        image.status = entity.status.value
        image.signed = True
        return await self.repos.container_images.update(image)

    async def publish_image(self, tenant_id: str, image_id: str) -> ContainerImageModel:
        image = await self.repos.container_images.get_or_404(image_id)
        entity = _to_entity(image)
        entity.publish()
        image.status = entity.status.value
        return await self.repos.container_images.update(image)

    async def deprecate_image(self, tenant_id: str, image_id: str) -> ContainerImageModel:
        image = await self.repos.container_images.get_or_404(image_id)
        entity = _to_entity(image)
        entity.deprecate()
        image.status = entity.status.value
        return await self.repos.container_images.update(image)

    async def quarantine_image(self, tenant_id: str, image_id: str) -> ContainerImageModel:
        image = await self.repos.container_images.get_or_404(image_id)
        entity = _to_entity(image)
        entity.quarantine()
        image.status = entity.status.value
        return await self.repos.container_images.update(image)

    async def retry_build(self, tenant_id: str, image_id: str) -> ContainerImageModel:
        image = await self.repos.container_images.get_or_404(image_id)
        entity = _to_entity(image)
        entity.retry_build()
        image.status = entity.status.value
        return await self.repos.container_images.update(image)

    async def list_versions(self, tenant_id: str, repository: str) -> list[ContainerImageModel]:
        return await self.repos.container_images.list_for_repository(tenant_id, repository)

    async def prune_old_versions(self, tenant_id: str, repository: str) -> int:
        """Soft-deletes published images beyond `image_version_retention_count`,
        oldest first — mirroring the Secrets Management module's
        version-retention pruning after rotation."""
        images = await self.repos.container_images.list_for_repository(tenant_id, repository)
        published = [i for i in images if i.status == ImageStatus.PUBLISHED.value]
        published.sort(key=lambda i: _aware(i.created_at), reverse=True)
        retain = self.settings.image_version_retention_count
        pruned = 0
        for stale in published[retain:]:
            await self.repos.container_images.delete(stale)
            pruned += 1
        return pruned
