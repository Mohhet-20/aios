import pytest

from release_platform.artifacts.artifact_service import ArtifactService
from release_platform.core.exceptions import NotFoundError, UnsupportedArtifactTypeError

pytestmark = pytest.mark.asyncio

TENANT = "t-artifacts"


async def test_register_artifact_rejects_unsupported_type(repos):
    svc = ArtifactService(repos)
    with pytest.raises(UnsupportedArtifactTypeError):
        await svc.register_artifact(TENANT, release_id="r1", artifact_type="floppy_disk", name="x", version="1.0.0")


async def test_register_and_get_artifact(repos):
    svc = ArtifactService(repos)
    artifact = await svc.register_artifact(
        TENANT, release_id="r1", artifact_type="docker_image", name="aios-backend", version="1.0.0", checksum="abc123",
    )
    assert artifact.signed is False
    fetched = await svc.get_or_404(TENANT, artifact.id)
    assert fetched.id == artifact.id


async def test_get_or_404_raises_for_missing(repos):
    svc = ArtifactService(repos)
    with pytest.raises(NotFoundError):
        await svc.get_or_404(TENANT, "nonexistent-id")


async def test_list_for_release_filters_by_type(repos):
    svc = ArtifactService(repos)
    await svc.register_artifact(TENANT, release_id="r2", artifact_type="docker_image", name="backend", version="1.0.0")
    await svc.register_artifact(TENANT, release_id="r2", artifact_type="helm_chart", name="backend-chart", version="1.0.0")
    docker_only = await svc.list_for_release(TENANT, "r2", artifact_type="docker_image")
    assert len(docker_only) == 1
    all_artifacts = await svc.list_for_release(TENANT, "r2")
    assert len(all_artifacts) == 2
