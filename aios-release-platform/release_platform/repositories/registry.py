"""RepositoryRegistry: per-request unit-of-work that lazily
instantiates and memoizes one repository per model, all sharing the
same AsyncSession — identical pattern to every prior AIOS platform."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from release_platform.repositories.analytics_repository import DeploymentMetricRepository, ReleaseAdoptionSnapshotRepository
from release_platform.repositories.artifact_distribution_repository import (
    ArtifactRepository,
    DistributionChannelRepository,
    DistributionEntryRepository,
)
from release_platform.repositories.deployment_repository import DeploymentRepository
from release_platform.repositories.environment_repository import EnvironmentRepository
from release_platform.repositories.feature_flag_repository import FeatureFlagOverrideRepository, FeatureFlagRepository
from release_platform.repositories.license_repository import LicenseRepository
from release_platform.repositories.release_versioning_repository import (
    CompatibilityEntryRepository,
    ReleaseRepository,
    VersionHistoryRepository,
)
from release_platform.repositories.rollback_repository import RollbackRepository
from release_platform.repositories.rollout_repository import RolloutRepository
from release_platform.repositories.security_repository import (
    ArtifactSignatureRepository,
    ReleaseApprovalRepository,
    SbomRepository,
)
from release_platform.repositories.update_repository import UpdateJobRepository
from release_platform.repositories.validation_repository import HealthCheckRunRepository


class RepositoryRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._repos: dict[str, object] = {}

    def _get(self, key: str, cls: type):
        if key not in self._repos:
            self._repos[key] = cls(self.session)
        return self._repos[key]

    # -- release & version management --
    @property
    def releases(self) -> ReleaseRepository:
        return self._get("releases", ReleaseRepository)

    @property
    def version_history(self) -> VersionHistoryRepository:
        return self._get("version_history", VersionHistoryRepository)

    @property
    def compatibility_entries(self) -> CompatibilityEntryRepository:
        return self._get("compatibility_entries", CompatibilityEntryRepository)

    # -- artifact management & distribution --
    @property
    def artifacts(self) -> ArtifactRepository:
        return self._get("artifacts", ArtifactRepository)

    @property
    def distribution_channels(self) -> DistributionChannelRepository:
        return self._get("distribution_channels", DistributionChannelRepository)

    @property
    def distribution_entries(self) -> DistributionEntryRepository:
        return self._get("distribution_entries", DistributionEntryRepository)

    # -- deployment orchestration --
    @property
    def deployments(self) -> DeploymentRepository:
        return self._get("deployments", DeploymentRepository)

    # -- rollout engine --
    @property
    def rollouts(self) -> RolloutRepository:
        return self._get("rollouts", RolloutRepository)

    # -- feature flag platform --
    @property
    def feature_flags(self) -> FeatureFlagRepository:
        return self._get("feature_flags", FeatureFlagRepository)

    @property
    def feature_flag_overrides(self) -> FeatureFlagOverrideRepository:
        return self._get("feature_flag_overrides", FeatureFlagOverrideRepository)

    # -- update infrastructure --
    @property
    def update_jobs(self) -> UpdateJobRepository:
        return self._get("update_jobs", UpdateJobRepository)

    # -- license management --
    @property
    def licenses(self) -> LicenseRepository:
        return self._get("licenses", LicenseRepository)

    # -- environment management --
    @property
    def environments(self) -> EnvironmentRepository:
        return self._get("environments", EnvironmentRepository)

    # -- deployment validation --
    @property
    def health_check_runs(self) -> HealthCheckRunRepository:
        return self._get("health_check_runs", HealthCheckRunRepository)

    # -- rollback engine --
    @property
    def rollbacks(self) -> RollbackRepository:
        return self._get("rollbacks", RollbackRepository)

    # -- security & supply chain --
    @property
    def sboms(self) -> SbomRepository:
        return self._get("sboms", SbomRepository)

    @property
    def artifact_signatures(self) -> ArtifactSignatureRepository:
        return self._get("artifact_signatures", ArtifactSignatureRepository)

    @property
    def release_approvals(self) -> ReleaseApprovalRepository:
        return self._get("release_approvals", ReleaseApprovalRepository)

    # -- observability & release analytics --
    @property
    def deployment_metrics(self) -> DeploymentMetricRepository:
        return self._get("deployment_metrics", DeploymentMetricRepository)

    @property
    def adoption_snapshots(self) -> ReleaseAdoptionSnapshotRepository:
        return self._get("adoption_snapshots", ReleaseAdoptionSnapshotRepository)
