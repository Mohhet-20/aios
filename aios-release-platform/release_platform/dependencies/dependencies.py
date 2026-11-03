"""FastAPI dependency wiring: DB session -> RepositoryRegistry ->
every service. Auth is intentionally minimal here, matching every
sibling AIOS platform: this platform expects to sit behind an
already-authenticated gateway (in practice, the Identity Platform)
that forwards the caller's tenant via `X-Tenant-Id` and, where
relevant, the acting principal via `X-User-Id`. Every service is
built fresh per request off a per-request `RepositoryRegistry`/
`AsyncSession`, since a session must never be shared across
concurrent requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from release_platform.analytics.analytics_service import AdoptionSnapshotService, DeploymentMetricService
from release_platform.artifacts.artifact_service import ArtifactService
from release_platform.config.settings import Settings, get_settings
from release_platform.database.session import session_scope
from release_platform.deployment.deployment_service import DeploymentService
from release_platform.distribution.distribution_service import DistributionChannelService, DistributionEntryService
from release_platform.environments.environment_service import EnvironmentService
from release_platform.feature_flags.feature_flag_service import FeatureFlagOverrideService, FeatureFlagService
from release_platform.licensing.license_service import LicenseService
from release_platform.release_engineering.release_service import ReleaseService
from release_platform.release_engineering.version_service import VersionService
from release_platform.repositories.registry import RepositoryRegistry
from release_platform.rollback.rollback_service import RollbackService
from release_platform.rollouts.rollout_service import RolloutService
from release_platform.security.release_approval_service import ReleaseApprovalService
from release_platform.security.sbom_service import SbomService
from release_platform.security.signature_service import ArtifactSignatureService
from release_platform.updates.update_service import UpdateJobService
from release_platform.validation.health_check_service import HealthCheckService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Delegates to `session_scope`, which commits on a clean exit and
    rolls back on any exception — a request handled through the REST
    API needs its writes to actually persist once the response is
    returned."""
    async for session in session_scope():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session)) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
    return x_tenant_id


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str | None:
    """Unlike the tenant header, the actor header is optional — some of
    what this platform tracks (automated rollouts, scheduled updates,
    health-check sweeps) legitimately comes from a process with no
    human actor behind it."""
    return x_user_id


# -- release & version management ----------------------------------------------------------------------
async def get_release_service(repos: RepositoryRegistry = Depends(get_repos)) -> ReleaseService:
    return ReleaseService(repos)


async def get_version_service(repos: RepositoryRegistry = Depends(get_repos)) -> VersionService:
    return VersionService(repos)


# -- artifact management & distribution -------------------------------------------------------------------
async def get_artifact_service(repos: RepositoryRegistry = Depends(get_repos)) -> ArtifactService:
    return ArtifactService(repos)


async def get_distribution_channel_service(repos: RepositoryRegistry = Depends(get_repos)) -> DistributionChannelService:
    return DistributionChannelService(repos)


async def get_distribution_entry_service(repos: RepositoryRegistry = Depends(get_repos)) -> DistributionEntryService:
    return DistributionEntryService(repos)


# -- deployment orchestration --------------------------------------------------------------------------
async def get_deployment_service(repos: RepositoryRegistry = Depends(get_repos)) -> DeploymentService:
    return DeploymentService(repos)


# -- rollout engine -----------------------------------------------------------------------------------------
async def get_rollout_service(repos: RepositoryRegistry = Depends(get_repos)) -> RolloutService:
    return RolloutService(repos)


# -- feature flag platform ------------------------------------------------------------------------------------
async def get_feature_flag_service(repos: RepositoryRegistry = Depends(get_repos)) -> FeatureFlagService:
    return FeatureFlagService(repos)


async def get_feature_flag_override_service(repos: RepositoryRegistry = Depends(get_repos)) -> FeatureFlagOverrideService:
    return FeatureFlagOverrideService(repos)


# -- update infrastructure ------------------------------------------------------------------------------------
async def get_update_job_service(repos: RepositoryRegistry = Depends(get_repos)) -> UpdateJobService:
    return UpdateJobService(repos)


# -- license management ------------------------------------------------------------------------------------------
async def get_license_service(repos: RepositoryRegistry = Depends(get_repos)) -> LicenseService:
    return LicenseService(repos)


# -- environment management ------------------------------------------------------------------------------------------
async def get_environment_service(repos: RepositoryRegistry = Depends(get_repos)) -> EnvironmentService:
    return EnvironmentService(repos)


# -- deployment validation ----------------------------------------------------------------------------------------
async def get_health_check_service(repos: RepositoryRegistry = Depends(get_repos)) -> HealthCheckService:
    return HealthCheckService(repos)


# -- rollback engine -----------------------------------------------------------------------------------------
async def get_rollback_service(repos: RepositoryRegistry = Depends(get_repos)) -> RollbackService:
    return RollbackService(repos)


# -- security & supply chain -----------------------------------------------------------------------------------------
async def get_sbom_service(repos: RepositoryRegistry = Depends(get_repos)) -> SbomService:
    return SbomService(repos)


async def get_artifact_signature_service(repos: RepositoryRegistry = Depends(get_repos)) -> ArtifactSignatureService:
    return ArtifactSignatureService(repos)


async def get_release_approval_service(repos: RepositoryRegistry = Depends(get_repos)) -> ReleaseApprovalService:
    return ReleaseApprovalService(repos)


# -- observability & release analytics -----------------------------------------------------------------------------------------
async def get_deployment_metric_service(repos: RepositoryRegistry = Depends(get_repos)) -> DeploymentMetricService:
    return DeploymentMetricService(repos)


async def get_adoption_snapshot_service(repos: RepositoryRegistry = Depends(get_repos)) -> AdoptionSnapshotService:
    return AdoptionSnapshotService(repos)
