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

from infra_platform.artifacts.artifact_service import ArtifactService, ArtifactVersionService
from infra_platform.autoscaling.autoscaling_service import ScalingPolicyService
from infra_platform.cicd.cicd_service import DeploymentGateService, PipelineRunService, PipelineService, ReleaseService
from infra_platform.cloud.cloud_service import CloudAccountService, CloudResourceService
from infra_platform.config.settings import Settings, get_settings
from infra_platform.containers.image_service import ImageRegistryService
from infra_platform.database.session import session_scope
from infra_platform.deployment.deployment_service import DeploymentService, FeatureFlagService
from infra_platform.experiments.experiment_service import ExperimentRunService, ExperimentService
from infra_platform.feature_store.feature_store_service import FeatureGroupService, FeatureService
from infra_platform.inference.inference_service import InferenceRouteService, InferenceServiceService
from infra_platform.infra_security.security_service import InfraRoleBindingService, NetworkPolicyService, RuntimePolicyService
from infra_platform.kubernetes.k8s_service import (
    AutoscalerService,
    ClusterService,
    K8sResourceService,
    NamespaceService,
    NodePoolService,
    ResourceQuotaService,
)
from infra_platform.model_registry.registry_service import ModelLineageService, ModelRegistryService, ModelVersionService
from infra_platform.observability.observability_service import ClusterHealthService, InfraMetricService
from infra_platform.recovery.recovery_service import (
    BackupService,
    FailoverService,
    RecoveryExecutionService,
    RecoveryPlanService,
    SnapshotService,
)
from infra_platform.repositories.registry import RepositoryRegistry


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Delegates to `session_scope`, which commits on a clean exit and
    rolls back on any exception — a request handled through the REST
    API needs its writes to actually persist once the response is
    returned."""
    async for session in session_scope():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session, scope="function")) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
    return x_tenant_id


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str | None:
    """Unlike the tenant header, the actor header is optional — some
    of what this platform tracks (scheduled retention sweeps, CI
    triggers, automated scaling decisions) legitimately comes from a
    process with no human actor behind it."""
    return x_user_id


# -- containers ----------------------------------------------------------------------------
async def get_image_registry_service(repos: RepositoryRegistry = Depends(get_repos)) -> ImageRegistryService:
    return ImageRegistryService(repos)


# -- kubernetes ------------------------------------------------------------------------------
async def get_cluster_service(repos: RepositoryRegistry = Depends(get_repos)) -> ClusterService:
    return ClusterService(repos)


async def get_node_pool_service(repos: RepositoryRegistry = Depends(get_repos)) -> NodePoolService:
    return NodePoolService(repos)


async def get_namespace_service(repos: RepositoryRegistry = Depends(get_repos)) -> NamespaceService:
    return NamespaceService(repos)


async def get_resource_quota_service(repos: RepositoryRegistry = Depends(get_repos)) -> ResourceQuotaService:
    return ResourceQuotaService(repos)


async def get_k8s_resource_service(repos: RepositoryRegistry = Depends(get_repos)) -> K8sResourceService:
    return K8sResourceService(repos)


async def get_k8s_autoscaler_service(repos: RepositoryRegistry = Depends(get_repos)) -> AutoscalerService:
    return AutoscalerService(repos)


# -- cicd --------------------------------------------------------------------------------------
async def get_pipeline_service(repos: RepositoryRegistry = Depends(get_repos)) -> PipelineService:
    return PipelineService(repos)


async def get_pipeline_run_service(repos: RepositoryRegistry = Depends(get_repos)) -> PipelineRunService:
    return PipelineRunService(repos)


async def get_deployment_gate_service(repos: RepositoryRegistry = Depends(get_repos)) -> DeploymentGateService:
    return DeploymentGateService(repos)


async def get_release_service(repos: RepositoryRegistry = Depends(get_repos)) -> ReleaseService:
    return ReleaseService(repos)


# -- model lifecycle -----------------------------------------------------------------------
async def get_model_registry_service(repos: RepositoryRegistry = Depends(get_repos)) -> ModelRegistryService:
    return ModelRegistryService(repos)


async def get_model_version_service(repos: RepositoryRegistry = Depends(get_repos)) -> ModelVersionService:
    return ModelVersionService(repos)


async def get_model_lineage_service(repos: RepositoryRegistry = Depends(get_repos)) -> ModelLineageService:
    return ModelLineageService(repos)


# -- experiments -----------------------------------------------------------------------------
async def get_experiment_service(repos: RepositoryRegistry = Depends(get_repos)) -> ExperimentService:
    return ExperimentService(repos)


async def get_experiment_run_service(repos: RepositoryRegistry = Depends(get_repos)) -> ExperimentRunService:
    return ExperimentRunService(repos)


# -- feature store ---------------------------------------------------------------------------
async def get_feature_group_service(repos: RepositoryRegistry = Depends(get_repos)) -> FeatureGroupService:
    return FeatureGroupService(repos)


async def get_feature_service(repos: RepositoryRegistry = Depends(get_repos)) -> FeatureService:
    return FeatureService(repos)


# -- artifacts -------------------------------------------------------------------------------
async def get_artifact_service(repos: RepositoryRegistry = Depends(get_repos)) -> ArtifactService:
    return ArtifactService(repos)


async def get_artifact_version_service(repos: RepositoryRegistry = Depends(get_repos)) -> ArtifactVersionService:
    return ArtifactVersionService(repos)


# -- inference -------------------------------------------------------------------------------
async def get_inference_service_service(repos: RepositoryRegistry = Depends(get_repos)) -> InferenceServiceService:
    return InferenceServiceService(repos)


async def get_inference_route_service(repos: RepositoryRegistry = Depends(get_repos)) -> InferenceRouteService:
    return InferenceRouteService(repos)


# -- deployment strategies -------------------------------------------------------------------
async def get_deployment_service(repos: RepositoryRegistry = Depends(get_repos)) -> DeploymentService:
    return DeploymentService(repos)


async def get_feature_flag_service(repos: RepositoryRegistry = Depends(get_repos)) -> FeatureFlagService:
    return FeatureFlagService(repos)


# -- autoscaling -----------------------------------------------------------------------------
async def get_scaling_policy_service(repos: RepositoryRegistry = Depends(get_repos)) -> ScalingPolicyService:
    return ScalingPolicyService(repos)


# -- multi-cloud -----------------------------------------------------------------------------
async def get_cloud_account_service(repos: RepositoryRegistry = Depends(get_repos)) -> CloudAccountService:
    return CloudAccountService(repos)


async def get_cloud_resource_service(repos: RepositoryRegistry = Depends(get_repos)) -> CloudResourceService:
    return CloudResourceService(repos)


# -- disaster recovery -----------------------------------------------------------------------
async def get_backup_service(repos: RepositoryRegistry = Depends(get_repos)) -> BackupService:
    return BackupService(repos)


async def get_snapshot_service(repos: RepositoryRegistry = Depends(get_repos)) -> SnapshotService:
    return SnapshotService(repos)


async def get_recovery_plan_service(repos: RepositoryRegistry = Depends(get_repos)) -> RecoveryPlanService:
    return RecoveryPlanService(repos)


async def get_recovery_execution_service(repos: RepositoryRegistry = Depends(get_repos)) -> RecoveryExecutionService:
    return RecoveryExecutionService(repos)


async def get_failover_service(repos: RepositoryRegistry = Depends(get_repos)) -> FailoverService:
    return FailoverService(repos)


# -- observability ---------------------------------------------------------------------------
async def get_infra_metric_service(repos: RepositoryRegistry = Depends(get_repos)) -> InfraMetricService:
    return InfraMetricService(repos)


async def get_cluster_health_service(repos: RepositoryRegistry = Depends(get_repos)) -> ClusterHealthService:
    return ClusterHealthService(repos)


# -- security & governance -------------------------------------------------------------------
async def get_network_policy_service(repos: RepositoryRegistry = Depends(get_repos)) -> NetworkPolicyService:
    return NetworkPolicyService(repos)


async def get_runtime_policy_service(repos: RepositoryRegistry = Depends(get_repos)) -> RuntimePolicyService:
    return RuntimePolicyService(repos)


async def get_infra_role_binding_service(repos: RepositoryRegistry = Depends(get_repos)) -> InfraRoleBindingService:
    return InfraRoleBindingService(repos)
