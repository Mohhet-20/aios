"""Maps the platform's domain exception hierarchy (core/exceptions.py)
to HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either. Order matters: this is checked top-to-bottom,
so subclasses are listed before their parent class."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from infra_platform.core.exceptions import (
    ArtifactError,
    ArtifactNotFoundError,
    AuthorizationError,
    AutoscalingError,
    BackupFailedError,
    ClusterNotFoundError,
    ClusterNotHealthyError,
    CloudError,
    CloudResourceError,
    ConcurrentModificationError,
    ConflictError,
    ContainerError,
    DeploymentError,
    DeploymentFailedError,
    DeploymentGateBlockedError,
    ExperimentError,
    FailoverError,
    FeatureNotFoundError,
    FeatureStoreError,
    FeatureValidationError,
    ImageAlreadyPublishedError,
    ImageNotFoundError,
    ImageScanFailedError,
    ImageSigningRequiredError,
    InferenceError,
    InferenceServiceUnavailableError,
    InfraPlatformError,
    InfraSecurityError,
    InvalidTransitionError,
    KubernetesError,
    ModelApprovalRequiredError,
    ModelPromotionError,
    ModelRegistryError,
    ModelVersionNotFoundError,
    NamespaceError,
    NetworkPolicyViolationError,
    NotFoundError,
    ObservabilityError,
    PermissionDeniedError,
    PipelineError,
    PipelineRunFailedError,
    RecoveryError,
    RecoveryPlanNotReadyError,
    ReleaseError,
    ResourceQuotaExceededError,
    RollbackError,
    RunAlreadyFinishedError,
    RunNotFoundError,
    RuntimePolicyViolationError,
    ScalingPolicyError,
    TenantIsolationError,
    TrafficSplitError,
    UnsupportedProviderError,
    ValidationError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[InfraPlatformError], int]] = [
    (NotFoundError, 404),
    (ImageNotFoundError, 404),
    (ImageScanFailedError, 422),
    (ImageSigningRequiredError, 403),
    (ImageAlreadyPublishedError, 409),
    (ContainerError, 400),
    (ClusterNotFoundError, 404),
    (ClusterNotHealthyError, 409),
    (ResourceQuotaExceededError, 422),
    (NamespaceError, 409),
    (KubernetesError, 400),
    (PipelineRunFailedError, 422),
    (DeploymentGateBlockedError, 423),  # 423 Locked
    (ReleaseError, 409),
    (PipelineError, 400),
    (ModelVersionNotFoundError, 404),
    (ModelApprovalRequiredError, 403),
    (ModelPromotionError, 409),
    (ModelRegistryError, 400),
    (RunNotFoundError, 404),
    (RunAlreadyFinishedError, 409),
    (ExperimentError, 400),
    (FeatureNotFoundError, 404),
    (FeatureValidationError, 422),
    (FeatureStoreError, 400),
    (ArtifactNotFoundError, 404),
    (ArtifactError, 400),
    (InferenceServiceUnavailableError, 503),
    (InferenceError, 400),
    (DeploymentFailedError, 422),
    (RollbackError, 409),
    (TrafficSplitError, 422),
    (DeploymentError, 400),
    (ScalingPolicyError, 400),
    (AutoscalingError, 429),  # cooldown-in-effect reads naturally as rate-limited
    (CloudResourceError, 404),
    (UnsupportedProviderError, 422),
    (CloudError, 400),
    (BackupFailedError, 422),
    (RecoveryPlanNotReadyError, 409),
    (FailoverError, 409),
    (RecoveryError, 400),
    (ObservabilityError, 400),
    (NetworkPolicyViolationError, 403),
    (RuntimePolicyViolationError, 403),
    (InfraSecurityError, 400),
    (TenantIsolationError, 403),
    (PermissionDeniedError, 403),
    (AuthorizationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ValidationError, 422),
]


def _status_for(exc: InfraPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InfraPlatformError)
    async def _handle_platform_error(request: Request, exc: InfraPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
