"""Exception hierarchy for the Enterprise Production Infrastructure &
MLOps Platform."""
from __future__ import annotations


class InfraPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(InfraPlatformError):
    pass


class ValidationError(InfraPlatformError):
    pass


class ConflictError(InfraPlatformError):
    pass


class ConcurrentModificationError(InfraPlatformError):
    pass


class AuthorizationError(InfraPlatformError):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


class TenantIsolationError(AuthorizationError):
    pass


class InvalidTransitionError(InfraPlatformError):
    """Raised on an illegal lifecycle transition (image, pipeline run,
    model version, deployment, cluster, backup/recovery, etc.)."""


# -- containers / image registry ----------------------------------------------------------

class ContainerError(InfraPlatformError):
    pass


class ImageNotFoundError(ContainerError):
    pass


class ImageScanFailedError(ContainerError):
    """Raised when a critical-severity scan finding blocks publish
    under `image_scan_critical_block`."""


class ImageSigningRequiredError(ContainerError):
    pass


class ImageAlreadyPublishedError(ContainerError):
    pass


# -- kubernetes -----------------------------------------------------------------------------

class KubernetesError(InfraPlatformError):
    pass


class ClusterNotFoundError(KubernetesError):
    pass


class ClusterNotHealthyError(KubernetesError):
    pass


class ResourceQuotaExceededError(KubernetesError):
    pass


class NamespaceError(KubernetesError):
    pass


# -- cicd -------------------------------------------------------------------------------------

class PipelineError(InfraPlatformError):
    pass


class PipelineRunFailedError(PipelineError):
    pass


class DeploymentGateBlockedError(PipelineError):
    pass


class ReleaseError(PipelineError):
    pass


# -- model lifecycle --------------------------------------------------------------------------

class ModelRegistryError(InfraPlatformError):
    pass


class ModelVersionNotFoundError(ModelRegistryError):
    pass


class ModelApprovalRequiredError(ModelRegistryError):
    pass


class ModelPromotionError(ModelRegistryError):
    pass


# -- experiments --------------------------------------------------------------------------------

class ExperimentError(InfraPlatformError):
    pass


class RunNotFoundError(ExperimentError):
    pass


class RunAlreadyFinishedError(ExperimentError):
    pass


# -- feature store -----------------------------------------------------------------------------

class FeatureStoreError(InfraPlatformError):
    pass


class FeatureValidationError(FeatureStoreError):
    pass


class FeatureNotFoundError(FeatureStoreError):
    pass


# -- artifacts ----------------------------------------------------------------------------------

class ArtifactError(InfraPlatformError):
    pass


class ArtifactNotFoundError(ArtifactError):
    pass


# -- inference ----------------------------------------------------------------------------------

class InferenceError(InfraPlatformError):
    pass


class InferenceServiceUnavailableError(InferenceError):
    pass


# -- deployment strategies ------------------------------------------------------------------------

class DeploymentError(InfraPlatformError):
    pass


class DeploymentFailedError(DeploymentError):
    pass


class RollbackError(DeploymentError):
    pass


class TrafficSplitError(DeploymentError):
    pass


# -- autoscaling --------------------------------------------------------------------------------

class AutoscalingError(InfraPlatformError):
    pass


class ScalingPolicyError(AutoscalingError):
    pass


# -- multi-cloud --------------------------------------------------------------------------------

class CloudError(InfraPlatformError):
    pass


class CloudResourceError(CloudError):
    pass


class UnsupportedProviderError(CloudError):
    pass


# -- disaster recovery --------------------------------------------------------------------------

class RecoveryError(InfraPlatformError):
    pass


class BackupFailedError(RecoveryError):
    pass


class RecoveryPlanNotReadyError(RecoveryError):
    pass


class FailoverError(RecoveryError):
    pass


# -- observability ------------------------------------------------------------------------------

class ObservabilityError(InfraPlatformError):
    pass


# -- security -----------------------------------------------------------------------------------

class InfraSecurityError(InfraPlatformError):
    pass


class NetworkPolicyViolationError(InfraSecurityError):
    pass


class RuntimePolicyViolationError(InfraSecurityError):
    pass
