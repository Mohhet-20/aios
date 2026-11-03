"""Software Bill of Materials records, one per artifact. `content_ref`
is a pointer to where the actual SBOM document lives (object storage,
a git blob, etc.) — this service tracks that a bill of materials was
generated and where to find it, it does not itself generate SBOM
content from a real dependency graph."""
from __future__ import annotations

from release_platform.config.settings import get_settings
from release_platform.core.exceptions import SbomNotFoundError
from release_platform.models.security import SbomModel
from release_platform.repositories.registry import RepositoryRegistry


class SbomService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def generate_sbom(self, tenant_id: str, *, artifact_id: str, format: str = "cyclonedx", content_ref: str = "") -> SbomModel:
        sbom = SbomModel(tenant_id=tenant_id, artifact_id=artifact_id, format=format, content_ref=content_ref)
        return await self.repos.sboms.add(sbom)

    async def list_for_artifact(self, tenant_id: str, artifact_id: str) -> list[SbomModel]:
        return await self.repos.sboms.list_for_artifact(tenant_id, artifact_id)

    async def assert_sbom_exists(self, tenant_id: str, artifact_id: str) -> None:
        if not self.settings.require_sbom:
            return
        if not await self.list_for_artifact(tenant_id, artifact_id):
            raise SbomNotFoundError(f"Artifact '{artifact_id}' has no SBOM on record")
