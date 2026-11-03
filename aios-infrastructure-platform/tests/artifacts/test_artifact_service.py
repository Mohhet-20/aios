"""Tests for Artifact Management: artifact CRUD (unique per
name+type), version sequencing, latest-version lookup, and checksum
verification."""
from __future__ import annotations

import pytest

from infra_platform.artifacts.artifact_service import ArtifactService, ArtifactVersionService
from infra_platform.core.exceptions import ArtifactError, ArtifactNotFoundError, NotFoundError

TENANT = "tenant-artifacts"


@pytest.mark.asyncio
async def test_create_artifact_unique_per_name_and_type(repos):
    service = ArtifactService(repos)
    await service.create_artifact(TENANT, name="churn-model", artifact_type="model")
    with pytest.raises(ArtifactError):
        await service.create_artifact(TENANT, name="churn-model", artifact_type="model")

    # same name, different type is fine
    other = await service.create_artifact(TENANT, name="churn-model", artifact_type="dataset")
    assert other.artifact_type == "dataset"


@pytest.mark.asyncio
async def test_add_version_sequencing_and_latest(repos):
    artifact_service = ArtifactService(repos)
    version_service = ArtifactVersionService(repos)
    artifact = await artifact_service.create_artifact(TENANT, name="embeddings-v1", artifact_type="embedding")

    v1 = await version_service.add_version(TENANT, artifact.id, storage_uri="s3://bucket/emb-v1.bin", checksum="abc123")
    v2 = await version_service.add_version(TENANT, artifact.id, storage_uri="s3://bucket/emb-v2.bin", checksum="def456")
    assert v1.version_number == 1
    assert v2.version_number == 2

    latest = await version_service.get_latest(TENANT, artifact.id)
    assert latest.id == v2.id

    all_versions = await version_service.list_for_artifact(TENANT, artifact.id)
    assert [v.version_number for v in all_versions] == [2, 1]


@pytest.mark.asyncio
async def test_get_latest_raises_when_no_versions(repos):
    artifact_service = ArtifactService(repos)
    version_service = ArtifactVersionService(repos)
    artifact = await artifact_service.create_artifact(TENANT, name="empty-artifact", artifact_type="prompt_template")
    with pytest.raises(ArtifactNotFoundError):
        await version_service.get_latest(TENANT, artifact.id)


@pytest.mark.asyncio
async def test_verify_checksum_match_and_mismatch(repos):
    artifact_service = ArtifactService(repos)
    version_service = ArtifactVersionService(repos)
    artifact = await artifact_service.create_artifact(TENANT, name="deploy-pkg", artifact_type="deployment_package")
    version = await version_service.add_version(TENANT, artifact.id, storage_uri="s3://bucket/pkg.tar.gz", checksum="sha256:abc")

    assert await version_service.verify_checksum(TENANT, version.id, expected_checksum="sha256:abc")

    with pytest.raises(ArtifactError):
        await version_service.verify_checksum(TENANT, version.id, expected_checksum="sha256:tampered")


@pytest.mark.asyncio
async def test_verify_checksum_missing_recorded_checksum_raises(repos):
    artifact_service = ArtifactService(repos)
    version_service = ArtifactVersionService(repos)
    artifact = await artifact_service.create_artifact(TENANT, name="no-checksum-pkg", artifact_type="deployment_package")
    version = await version_service.add_version(TENANT, artifact.id, storage_uri="s3://bucket/pkg2.tar.gz")

    with pytest.raises(ArtifactError):
        await version_service.verify_checksum(TENANT, version.id, expected_checksum="sha256:whatever")


@pytest.mark.asyncio
async def test_add_version_unknown_artifact_raises(repos):
    version_service = ArtifactVersionService(repos)
    with pytest.raises(NotFoundError):
        await version_service.add_version(TENANT, "no-such-artifact", storage_uri="s3://x")
