"""Artifact Management: build artifacts across the 11 declared types
(backend/frontend/SDK/CLI packages, Docker images, Kubernetes
manifests, Helm charts, Terraform modules, workflow/agent/prompt
templates), scoped to the release that produced them. `signed` starts
False and is flipped by the security module once a real signature
record is attached — this service only knows how to register and
list artifacts, not how to sign them."""
from __future__ import annotations

from release_platform.config.settings import get_settings
from release_platform.core.exceptions import ArtifactNotFoundError, UnsupportedArtifactTypeError
from release_platform.models.artifact_distribution import ArtifactModel
from release_platform.repositories.registry import RepositoryRegistry


class ArtifactService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, artifact_id: str) -> ArtifactModel:
        artifact = await self.repos.artifacts.get_or_404(artifact_id)
        if artifact.tenant_id != tenant_id:
            raise ArtifactNotFoundError(f"Artifact '{artifact_id}' not found for tenant '{tenant_id}'")
        return artifact

    async def register_artifact(
        self, tenant_id: str, *, release_id: str, artifact_type: str, name: str, version: str,
        checksum: str | None = None, storage_uri: str = "", size_bytes: int = 0,
    ) -> ArtifactModel:
        if artifact_type not in self.settings.artifact_types:
            raise UnsupportedArtifactTypeError(f"Unsupported artifact type '{artifact_type}'")
        artifact = ArtifactModel(
            tenant_id=tenant_id, release_id=release_id, artifact_type=artifact_type, name=name, version=version,
            checksum=checksum, storage_uri=storage_uri, size_bytes=size_bytes, signed=False,
        )
        return await self.repos.artifacts.add(artifact)

    async def list_for_release(self, tenant_id: str, release_id: str, *, artifact_type: str | None = None) -> list[ArtifactModel]:
        return await self.repos.artifacts.list_for_release(tenant_id, release_id, artifact_type=artifact_type)
