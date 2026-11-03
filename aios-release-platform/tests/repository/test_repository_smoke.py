"""Schema smoke test: every repository can round-trip a minimal row for
its model, and RepositoryRegistry memoizes one instance per repository."""
from __future__ import annotations

import datetime as dt

import pytest

from release_platform.models.analytics import DeploymentMetricModel, ReleaseAdoptionSnapshotModel
from release_platform.models.artifact_distribution import ArtifactModel, DistributionChannelModel, DistributionEntryModel
from release_platform.models.deployment import DeploymentModel
from release_platform.models.environment import EnvironmentModel
from release_platform.models.feature_flag import FeatureFlagModel, FeatureFlagOverrideModel
from release_platform.models.license import LicenseModel
from release_platform.models.release_versioning import CompatibilityEntryModel, ReleaseModel, VersionHistoryModel
from release_platform.models.rollback import RollbackModel
from release_platform.models.rollout import RolloutModel
from release_platform.models.security import ArtifactSignatureModel, ReleaseApprovalModel, SbomModel
from release_platform.models.update import UpdateJobModel
from release_platform.models.validation import HealthCheckRunModel

pytestmark = pytest.mark.asyncio


async def test_registry_memoizes_repositories(repos):
    assert repos.releases is repos.releases
    assert repos.deployments is repos.deployments
    assert repos.releases is not repos.deployments


async def test_release_versioning_round_trip(repos):
    release = await repos.releases.add(ReleaseModel(tenant_id="t1", version="1.0.0", channel="stable"))
    await repos.session.commit()
    await repos.version_history.add(VersionHistoryModel(tenant_id="t1", release_id=release.id, version="1.0.0", recorded_at=dt.datetime.now(dt.timezone.utc)))
    await repos.compatibility_entries.add(CompatibilityEntryModel(tenant_id="t1", version="1.0.0", component_ref="sdk:python", compatible_from="1.0.0"))
    await repos.session.commit()
    assert (await repos.releases.get_by_version("t1", "1.0.0")) is not None
    assert len(await repos.version_history.list_for_release("t1", release.id)) == 1


async def test_artifact_distribution_round_trip(repos):
    release = await repos.releases.add(ReleaseModel(tenant_id="t1", version="1.1.0", channel="stable"))
    artifact = await repos.artifacts.add(ArtifactModel(tenant_id="t1", release_id=release.id, artifact_type="docker_image", name="aios-backend", version="1.1.0"))
    channel = await repos.distribution_channels.add(DistributionChannelModel(tenant_id="t1", channel_type="docker_registry", name="primary-registry"))
    await repos.session.commit()
    await repos.distribution_entries.add(
        DistributionEntryModel(tenant_id="t1", artifact_id=artifact.id, channel_id=channel.id, published_at=dt.datetime.now(dt.timezone.utc))
    )
    await repos.session.commit()
    assert len(await repos.artifacts.list_for_release("t1", release.id)) == 1
    assert (await repos.distribution_channels.get_by_name("t1", "primary-registry")) is not None


async def test_deployment_and_rollout_round_trip(repos):
    env = await repos.environments.add(EnvironmentModel(tenant_id="t1", name="prod-us", environment_type="production"))
    release = await repos.releases.add(ReleaseModel(tenant_id="t1", version="1.2.0", channel="stable"))
    await repos.session.commit()
    deployment = await repos.deployments.add(
        DeploymentModel(tenant_id="t1", release_id=release.id, environment_id=env.id, target_type="cloud", status="queued")
    )
    await repos.session.commit()
    await repos.rollouts.add(RolloutModel(tenant_id="t1", deployment_id=deployment.id, strategy="canary", status="planned"))
    await repos.session.commit()
    assert len(await repos.deployments.list_for_tenant("t1")) >= 1
    assert len(await repos.rollouts.list_for_deployment("t1", deployment.id)) == 1


async def test_feature_flag_round_trip(repos):
    flag = await repos.feature_flags.add(FeatureFlagModel(tenant_id="t1", key="new-console", name="New Console", scope="global"))
    await repos.session.commit()
    await repos.feature_flag_overrides.add(FeatureFlagOverrideModel(tenant_id="t1", flag_id=flag.id, target_ref="org:acme", enabled=True))
    await repos.session.commit()
    assert (await repos.feature_flags.get_by_key("t1", "new-console")) is not None
    assert len(await repos.feature_flag_overrides.list_for_flag("t1", flag.id)) == 1


async def test_update_job_round_trip(repos):
    job = await repos.update_jobs.add(UpdateJobModel(tenant_id="t1", target_ref="install:acme-1", update_type="automatic", to_version="1.2.0"))
    await repos.session.commit()
    assert len(await repos.update_jobs.list_for_target("t1", "install:acme-1")) == 1
    assert (await repos.update_jobs.get(job.id)) is not None


async def test_license_round_trip(repos):
    lic = await repos.licenses.add(
        LicenseModel(tenant_id="t1", org_ref="org:acme", license_type="enterprise", seats_total=100, issued_at=dt.datetime.now(dt.timezone.utc))
    )
    await repos.session.commit()
    assert len(await repos.licenses.list_for_org("t1", "org:acme")) == 1
    assert (await repos.licenses.get(lic.id)) is not None


async def test_validation_and_rollback_round_trip(repos):
    env = await repos.environments.add(EnvironmentModel(tenant_id="t1", name="prod-eu", environment_type="production"))
    release = await repos.releases.add(ReleaseModel(tenant_id="t1", version="1.3.0", channel="stable"))
    await repos.session.commit()
    deployment = await repos.deployments.add(
        DeploymentModel(tenant_id="t1", release_id=release.id, environment_id=env.id, target_type="cloud", status="queued")
    )
    await repos.session.commit()
    await repos.health_check_runs.add(HealthCheckRunModel(tenant_id="t1", deployment_id=deployment.id, target="database", status="passed"))
    await repos.rollbacks.add(RollbackModel(tenant_id="t1", deployment_id=deployment.id, rollback_type="automatic", status="queued"))
    await repos.session.commit()
    assert len(await repos.health_check_runs.list_for_deployment("t1", deployment.id)) == 1
    assert len(await repos.rollbacks.list_for_deployment("t1", deployment.id)) == 1


async def test_security_supply_chain_round_trip(repos):
    release = await repos.releases.add(ReleaseModel(tenant_id="t1", version="1.4.0", channel="stable"))
    artifact = await repos.artifacts.add(ArtifactModel(tenant_id="t1", release_id=release.id, artifact_type="docker_image", name="aios-backend", version="1.4.0"))
    await repos.session.commit()
    await repos.sboms.add(SbomModel(tenant_id="t1", artifact_id=artifact.id, format="cyclonedx", content_ref="s3://sboms/1.4.0.json"))
    await repos.artifact_signatures.add(ArtifactSignatureModel(tenant_id="t1", artifact_id=artifact.id, signature="deadbeef", algorithm="sha256"))
    await repos.release_approvals.add(ReleaseApprovalModel(tenant_id="t1", release_id=release.id, approver_id="u1", decision="pending"))
    await repos.session.commit()
    assert len(await repos.sboms.list_for_artifact("t1", artifact.id)) == 1
    assert len(await repos.artifact_signatures.list_for_artifact("t1", artifact.id)) == 1
    assert len(await repos.release_approvals.list_for_release("t1", release.id)) == 1


async def test_analytics_round_trip(repos):
    await repos.deployment_metrics.add(DeploymentMetricModel(tenant_id="t1", metric_type="deployment_duration_seconds", value=42.0))
    await repos.adoption_snapshots.add(ReleaseAdoptionSnapshotModel(tenant_id="t1", version="1.4.0", adoption_pct=12.5))
    await repos.session.commit()
    assert len(await repos.deployment_metrics.list_for_tenant("t1")) == 1
    assert len(await repos.adoption_snapshots.list_for_version("t1", "1.4.0")) == 1
