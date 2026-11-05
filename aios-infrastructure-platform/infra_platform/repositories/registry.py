"""Unit-of-work: one shared `AsyncSession` backing every repository,
lazily memoized. Identical pattern to every other AIOS platform."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from infra_platform.repositories.artifacts_repository import ArtifactRepository, ArtifactVersionRepository
from infra_platform.repositories.autoscaling_repository import ScalingEventRepository, ScalingPolicyRepository
from infra_platform.repositories.cicd_repository import (
    DeploymentGateRepository,
    PipelineRepository,
    PipelineRunRepository,
    PipelineStageRunRepository,
    ReleaseRepository,
)
from infra_platform.repositories.cloud_repository import CloudAccountRepository, CloudResourceRepository
from infra_platform.repositories.containers_repository import ContainerImageRepository, ImageScanResultRepository, ImageSignatureRepository
from infra_platform.repositories.deployment_repository import (
    DeploymentEventRepository,
    DeploymentRepository,
    FeatureFlagRepository,
    TrafficSplitRepository,
)
from infra_platform.repositories.experiments_repository import (
    ExperimentRepository,
    ExperimentRunRepository,
    RunMetricRepository,
    RunParamRepository,
)
from infra_platform.repositories.feature_store_repository import FeatureGroupRepository, FeatureRepository, FeatureValidationRuleRepository
from infra_platform.repositories.inference_repository import InferenceRouteRepository, InferenceServiceRepository
from infra_platform.repositories.kubernetes_repository import (
    AutoscalerConfigRepository,
    ClusterRepository,
    K8sResourceRepository,
    NamespaceRepository,
    NodePoolRepository,
    ResourceQuotaRepository,
)
from infra_platform.repositories.model_registry_repository import (
    ModelApprovalRepository,
    ModelLineageEdgeRepository,
    ModelRegistryEntryRepository,
    ModelVersionRepository,
)
from infra_platform.repositories.observability_repository import ClusterHealthCheckRepository, InfraMetricRepository
from infra_platform.repositories.recovery_repository import (
    BackupRepository,
    FailoverEventRepository,
    RecoveryExecutionRepository,
    RecoveryPlanRepository,
    SnapshotRepository,
)
from infra_platform.repositories.security_repository import InfraRoleBindingRepository, NetworkPolicyRepository, RuntimePolicyRepository
from infra_platform.repositories.services_repository import ServiceRepository


class RepositoryRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[str, object] = {}

    def _get(self, key: str, cls: type):
        if key not in self._cache:
            self._cache[key] = cls(self.session)
        return self._cache[key]

    # -- services -----------------------------------------------------------------------
    @property
    def services(self) -> ServiceRepository:
        return self._get("services", ServiceRepository)

    # -- containers ---------------------------------------------------------------------
    @property
    def container_images(self) -> ContainerImageRepository:
        return self._get("container_images", ContainerImageRepository)

    @property
    def image_scan_results(self) -> ImageScanResultRepository:
        return self._get("image_scan_results", ImageScanResultRepository)

    @property
    def image_signatures(self) -> ImageSignatureRepository:
        return self._get("image_signatures", ImageSignatureRepository)

    # -- kubernetes ---------------------------------------------------------------------
    @property
    def clusters(self) -> ClusterRepository:
        return self._get("clusters", ClusterRepository)

    @property
    def node_pools(self) -> NodePoolRepository:
        return self._get("node_pools", NodePoolRepository)

    @property
    def namespaces(self) -> NamespaceRepository:
        return self._get("namespaces", NamespaceRepository)

    @property
    def k8s_resources(self) -> K8sResourceRepository:
        return self._get("k8s_resources", K8sResourceRepository)

    @property
    def resource_quotas(self) -> ResourceQuotaRepository:
        return self._get("resource_quotas", ResourceQuotaRepository)

    @property
    def autoscaler_configs(self) -> AutoscalerConfigRepository:
        return self._get("autoscaler_configs", AutoscalerConfigRepository)

    # -- cicd -----------------------------------------------------------------------------
    @property
    def pipelines(self) -> PipelineRepository:
        return self._get("pipelines", PipelineRepository)

    @property
    def pipeline_runs(self) -> PipelineRunRepository:
        return self._get("pipeline_runs", PipelineRunRepository)

    @property
    def pipeline_stage_runs(self) -> PipelineStageRunRepository:
        return self._get("pipeline_stage_runs", PipelineStageRunRepository)

    @property
    def deployment_gates(self) -> DeploymentGateRepository:
        return self._get("deployment_gates", DeploymentGateRepository)

    @property
    def releases(self) -> ReleaseRepository:
        return self._get("releases", ReleaseRepository)

    # -- model registry -------------------------------------------------------------------
    @property
    def model_registry_entries(self) -> ModelRegistryEntryRepository:
        return self._get("model_registry_entries", ModelRegistryEntryRepository)

    @property
    def model_versions(self) -> ModelVersionRepository:
        return self._get("model_versions", ModelVersionRepository)

    @property
    def model_approvals(self) -> ModelApprovalRepository:
        return self._get("model_approvals", ModelApprovalRepository)

    @property
    def model_lineage_edges(self) -> ModelLineageEdgeRepository:
        return self._get("model_lineage_edges", ModelLineageEdgeRepository)

    # -- experiments ------------------------------------------------------------------------
    @property
    def experiments(self) -> ExperimentRepository:
        return self._get("experiments", ExperimentRepository)

    @property
    def experiment_runs(self) -> ExperimentRunRepository:
        return self._get("experiment_runs", ExperimentRunRepository)

    @property
    def run_metrics(self) -> RunMetricRepository:
        return self._get("run_metrics", RunMetricRepository)

    @property
    def run_params(self) -> RunParamRepository:
        return self._get("run_params", RunParamRepository)

    # -- feature store ------------------------------------------------------------------------
    @property
    def feature_groups(self) -> FeatureGroupRepository:
        return self._get("feature_groups", FeatureGroupRepository)

    @property
    def features(self) -> FeatureRepository:
        return self._get("features", FeatureRepository)

    @property
    def feature_validation_rules(self) -> FeatureValidationRuleRepository:
        return self._get("feature_validation_rules", FeatureValidationRuleRepository)

    # -- artifacts ----------------------------------------------------------------------------
    @property
    def artifacts(self) -> ArtifactRepository:
        return self._get("artifacts", ArtifactRepository)

    @property
    def artifact_versions(self) -> ArtifactVersionRepository:
        return self._get("artifact_versions", ArtifactVersionRepository)

    # -- inference ----------------------------------------------------------------------------
    @property
    def inference_services(self) -> InferenceServiceRepository:
        return self._get("inference_services", InferenceServiceRepository)

    @property
    def inference_routes(self) -> InferenceRouteRepository:
        return self._get("inference_routes", InferenceRouteRepository)

    # -- deployment ---------------------------------------------------------------------------
    @property
    def deployments(self) -> DeploymentRepository:
        return self._get("deployments", DeploymentRepository)

    @property
    def traffic_splits(self) -> TrafficSplitRepository:
        return self._get("traffic_splits", TrafficSplitRepository)

    @property
    def feature_flags(self) -> FeatureFlagRepository:
        return self._get("feature_flags", FeatureFlagRepository)

    @property
    def deployment_events(self) -> DeploymentEventRepository:
        return self._get("deployment_events", DeploymentEventRepository)

    # -- autoscaling --------------------------------------------------------------------------
    @property
    def scaling_policies(self) -> ScalingPolicyRepository:
        return self._get("scaling_policies", ScalingPolicyRepository)

    @property
    def scaling_events(self) -> ScalingEventRepository:
        return self._get("scaling_events", ScalingEventRepository)

    # -- cloud ----------------------------------------------------------------------------------
    @property
    def cloud_accounts(self) -> CloudAccountRepository:
        return self._get("cloud_accounts", CloudAccountRepository)

    @property
    def cloud_resources(self) -> CloudResourceRepository:
        return self._get("cloud_resources", CloudResourceRepository)

    # -- recovery -------------------------------------------------------------------------------
    @property
    def backups(self) -> BackupRepository:
        return self._get("backups", BackupRepository)

    @property
    def snapshots(self) -> SnapshotRepository:
        return self._get("snapshots", SnapshotRepository)

    @property
    def recovery_plans(self) -> RecoveryPlanRepository:
        return self._get("recovery_plans", RecoveryPlanRepository)

    @property
    def recovery_executions(self) -> RecoveryExecutionRepository:
        return self._get("recovery_executions", RecoveryExecutionRepository)

    @property
    def failover_events(self) -> FailoverEventRepository:
        return self._get("failover_events", FailoverEventRepository)

    # -- observability ----------------------------------------------------------------------------
    @property
    def infra_metrics(self) -> InfraMetricRepository:
        return self._get("infra_metrics", InfraMetricRepository)

    @property
    def cluster_health_checks(self) -> ClusterHealthCheckRepository:
        return self._get("cluster_health_checks", ClusterHealthCheckRepository)

    # -- security ---------------------------------------------------------------------------------
    @property
    def network_policies(self) -> NetworkPolicyRepository:
        return self._get("network_policies", NetworkPolicyRepository)

    @property
    def runtime_policies(self) -> RuntimePolicyRepository:
        return self._get("runtime_policies", RuntimePolicyRepository)

    @property
    def infra_role_bindings(self) -> InfraRoleBindingRepository:
        return self._get("infra_role_bindings", InfraRoleBindingRepository)
