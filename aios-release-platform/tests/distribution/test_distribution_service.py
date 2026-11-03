import pytest

from release_platform.artifacts.artifact_service import ArtifactService
from release_platform.core.exceptions import ArtifactError, NotFoundError
from release_platform.distribution.distribution_service import DistributionChannelService, DistributionEntryService

pytestmark = pytest.mark.asyncio

TENANT = "t-distribution"


async def test_register_channel_rejects_unsupported_type(repos):
    svc = DistributionChannelService(repos)
    with pytest.raises(ArtifactError):
        await svc.register_channel(TENANT, channel_type="carrier_pigeon", name="pigeon-net")


async def test_register_and_list_channels(repos):
    svc = DistributionChannelService(repos)
    await svc.register_channel(TENANT, channel_type="docker_registry", name="primary-registry", endpoint_uri="https://registry.example.com")
    await svc.register_channel(TENANT, channel_type="helm_repository", name="primary-helm")
    docker_channels = await svc.list_channels(TENANT, channel_type="docker_registry")
    assert len(docker_channels) == 1


async def test_publish_artifact_requires_existing_artifact(repos):
    channel_svc = DistributionChannelService(repos)
    channel = await channel_svc.register_channel(TENANT, channel_type="docker_registry", name="reg-1")
    entry_svc = DistributionEntryService(repos)
    with pytest.raises(NotFoundError):
        await entry_svc.publish_artifact(TENANT, artifact_id="nonexistent", channel_id=channel.id)


async def test_publish_artifact_requires_existing_channel(repos):
    artifact_svc = ArtifactService(repos)
    artifact = await artifact_svc.register_artifact(TENANT, release_id="r1", artifact_type="docker_image", name="backend", version="1.0.0")
    entry_svc = DistributionEntryService(repos)
    with pytest.raises(NotFoundError):
        await entry_svc.publish_artifact(TENANT, artifact_id=artifact.id, channel_id="nonexistent")


async def test_publish_artifact_success(repos):
    artifact_svc = ArtifactService(repos)
    channel_svc = DistributionChannelService(repos)
    entry_svc = DistributionEntryService(repos)

    artifact = await artifact_svc.register_artifact(TENANT, release_id="r2", artifact_type="helm_chart", name="backend-chart", version="1.0.0")
    channel = await channel_svc.register_channel(TENANT, channel_type="helm_repository", name="helm-repo-1")

    entry = await entry_svc.publish_artifact(TENANT, artifact_id=artifact.id, channel_id=channel.id)
    assert entry.status == "published"

    published = await entry_svc.list_for_artifact(TENANT, artifact.id)
    assert len(published) == 1
