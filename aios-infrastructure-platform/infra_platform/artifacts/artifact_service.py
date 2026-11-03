"""Artifact Management: a single generic store for every artifact
type the platform produces — models, datasets, embeddings, prompt
templates, agent configs, workflow templates, evaluation reports,
training outputs, deployment packages — one `ArtifactModel` per named
artifact (unique per name+type), versioned beneath it with an opaque
`storage_uri` pointer ("own the pointer, not the data", the same
posture as the Security Platform's governed-asset registry and this
platform's own Model Registry). `verify_checksum` is the integrity
check a promotion or deployment step would run before trusting a
version's bytes."""
from __future__ import annotations

from infra_platform.core.exceptions import ArtifactError, ArtifactNotFoundError, NotFoundError
from infra_platform.models.artifacts import ArtifactModel, ArtifactVersionModel
from infra_platform.repositories.registry import RepositoryRegistry


class ArtifactService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_artifact(
        self, tenant_id: str, *, name: str, artifact_type: str, owner_id: str | None = None, description: str | None = None
    ) -> ArtifactModel:
        existing = await self.repos.artifacts.get_by_name_type(tenant_id, name, artifact_type)
        if existing is not None:
            raise ArtifactError(f"Artifact '{name}' of type '{artifact_type}' already exists")
        artifact = ArtifactModel(
            tenant_id=tenant_id, name=name, artifact_type=artifact_type, owner_id=owner_id, description=description
        )
        return await self.repos.artifacts.add(artifact)

    async def get(self, tenant_id: str, artifact_id: str) -> ArtifactModel:
        artifact = await self.repos.artifacts.get(artifact_id)
        if artifact is None or artifact.tenant_id != tenant_id:
            raise NotFoundError(f"Artifact '{artifact_id}' not found")
        return artifact

    async def list_by_type(self, tenant_id: str, artifact_type: str) -> list[ArtifactModel]:
        return await self.repos.artifacts.list_by_type(tenant_id, artifact_type)

    async def list_for_tenant(self, tenant_id: str) -> list[ArtifactModel]:
        return await self.repos.artifacts.list(filters={"tenant_id": tenant_id})


class ArtifactVersionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def add_version(
        self, tenant_id: str, artifact_id: str, *, storage_uri: str, size_bytes: int | None = None,
        checksum: str | None = None, artifact_metadata: dict | None = None,
    ) -> ArtifactVersionModel:
        artifact = await self.repos.artifacts.get(artifact_id)
        if artifact is None or artifact.tenant_id != tenant_id:
            raise NotFoundError(f"Artifact '{artifact_id}' not found")
        next_number = await self.repos.artifact_versions.get_latest_version_number(tenant_id, artifact_id) + 1
        version = ArtifactVersionModel(
            tenant_id=tenant_id, artifact_id=artifact_id, version_number=next_number, storage_uri=storage_uri,
            size_bytes=size_bytes, checksum=checksum, artifact_metadata=artifact_metadata or {},
        )
        return await self.repos.artifact_versions.add(version)

    async def get_latest(self, tenant_id: str, artifact_id: str) -> ArtifactVersionModel:
        versions = await self.repos.artifact_versions.list_for_artifact(tenant_id, artifact_id)
        if not versions:
            raise ArtifactNotFoundError(f"Artifact '{artifact_id}' has no versions")
        return versions[0]

    async def list_for_artifact(self, tenant_id: str, artifact_id: str) -> list[ArtifactVersionModel]:
        return await self.repos.artifact_versions.list_for_artifact(tenant_id, artifact_id)

    async def verify_checksum(self, tenant_id: str, version_id: str, *, expected_checksum: str) -> bool:
        version = await self.repos.artifact_versions.get(version_id)
        if version is None or version.tenant_id != tenant_id:
            raise ArtifactNotFoundError(f"ArtifactVersion '{version_id}' not found")
        if version.checksum is None:
            raise ArtifactError(f"ArtifactVersion '{version_id}' has no recorded checksum to verify against")
        if version.checksum != expected_checksum:
            raise ArtifactError(
                f"Checksum mismatch for ArtifactVersion '{version_id}': expected '{expected_checksum}', recorded '{version.checksum}'"
            )
        return True
