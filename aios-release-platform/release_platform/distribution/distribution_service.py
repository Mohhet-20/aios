"""Enterprise Distribution: channels (Docker/container registry, Helm
repository, package registry, private enterprise distribution, offline
bundle) and the publish record linking an artifact to a channel it was
pushed to. Channel type is validated against the `DistributionChannelType`
enum directly rather than a settings list, since — unlike artifact
types or release channels — this platform doesn't need per-tenant
configurability over which distribution mechanisms exist."""
from __future__ import annotations


from release_platform.artifacts.artifact_service import ArtifactService
from release_platform.core.exceptions import ArtifactError, DistributionChannelNotFoundError
from release_platform.domain.enums import DistributionChannelType
from release_platform.models.artifact_distribution import DistributionChannelModel, DistributionEntryModel
from release_platform.repositories.registry import RepositoryRegistry
from release_platform.clock import utc_now

_VALID_CHANNEL_TYPES = {c.value for c in DistributionChannelType}


class DistributionChannelService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def get_or_404(self, tenant_id: str, channel_id: str) -> DistributionChannelModel:
        channel = await self.repos.distribution_channels.get_or_404(channel_id)
        if channel.tenant_id != tenant_id:
            raise DistributionChannelNotFoundError(f"Distribution channel '{channel_id}' not found for tenant '{tenant_id}'")
        return channel

    async def register_channel(
        self, tenant_id: str, *, channel_type: str, name: str, endpoint_uri: str = ""
    ) -> DistributionChannelModel:
        if channel_type not in _VALID_CHANNEL_TYPES:
            raise ArtifactError(f"Unsupported distribution channel type '{channel_type}'")
        channel = DistributionChannelModel(tenant_id=tenant_id, channel_type=channel_type, name=name, endpoint_uri=endpoint_uri)
        return await self.repos.distribution_channels.add(channel)

    async def list_channels(self, tenant_id: str, *, channel_type: str | None = None) -> list[DistributionChannelModel]:
        return await self.repos.distribution_channels.list_for_tenant(tenant_id, channel_type=channel_type)


class DistributionEntryService:
    """Publishes an artifact to a channel. Both referenced rows are
    validated to exist (and belong to the caller's tenant) before the
    publish record is written, so a stray artifact_id/channel_id never
    silently produces an orphaned distribution entry."""

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.artifacts = ArtifactService(repos)
        self.channels = DistributionChannelService(repos)

    async def publish_artifact(self, tenant_id: str, *, artifact_id: str, channel_id: str) -> DistributionEntryModel:
        await self.artifacts.get_or_404(tenant_id, artifact_id)
        await self.channels.get_or_404(tenant_id, channel_id)
        entry = DistributionEntryModel(
            tenant_id=tenant_id, artifact_id=artifact_id, channel_id=channel_id,
            status="published", published_at=utc_now(),
        )
        return await self.repos.distribution_entries.add(entry)

    async def list_for_artifact(self, tenant_id: str, artifact_id: str) -> list[DistributionEntryModel]:
        return await self.repos.distribution_entries.list_for_artifact(tenant_id, artifact_id)
