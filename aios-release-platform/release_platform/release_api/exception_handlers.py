"""Maps the platform's domain exception hierarchy (core/exceptions.py)
to HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either. Order matters: this is checked top-to-bottom,
so subclasses are listed before their parent class."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from release_platform.core.exceptions import (
    ArtifactError,
    ArtifactNotFoundError,
    AuthorizationError,
    ChecksumMismatchError,
    ConcurrentModificationError,
    ConflictError,
    DeploymentError,
    DeploymentNotFoundError,
    DeploymentValidationError,
    DistributionChannelNotFoundError,
    EnvironmentManagementError,
    EnvironmentNotFoundError,
    FeatureFlagError,
    FeatureFlagNotFoundError,
    HealthCheckFailedError,
    IncompatibleVersionError,
    InvalidTransitionError,
    LicenseError,
    LicenseExpiredError,
    LicenseNotFoundError,
    NotFoundError,
    PermissionDeniedError,
    ReleaseAnalyticsError,
    ReleaseApprovalRequiredError,
    ReleaseError,
    ReleaseNotFoundError,
    ReleasePlatformError,
    RollbackError,
    RollbackNotFoundError,
    RolloutError,
    RolloutNotFoundError,
    SbomNotFoundError,
    SeatLimitExceededError,
    SignatureVerificationFailedError,
    SnapshotNotFoundError,
    SupplyChainError,
    TenantIsolationError,
    UnsupportedArtifactTypeError,
    UnsupportedDeploymentTargetError,
    UnsupportedEnvironmentTypeError,
    UnsupportedFeatureFlagScopeError,
    UnsupportedRollbackTypeError,
    UnsupportedRolloutStrategyError,
    UnsupportedReleaseChannelError,
    UnsupportedUpdateTypeError,
    UpdateError,
    UpdateJobNotFoundError,
    ValidationError,
    VersionCompatibilityError,
    VersionNotFoundError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[ReleasePlatformError], int]] = [
    (NotFoundError, 404),
    # release & version management
    (ReleaseNotFoundError, 404),
    (VersionNotFoundError, 404),
    (UnsupportedReleaseChannelError, 422),
    (IncompatibleVersionError, 422),
    (ReleaseError, 400),
    # artifact management & distribution
    (ArtifactNotFoundError, 404),
    (DistributionChannelNotFoundError, 404),
    (UnsupportedArtifactTypeError, 422),
    (ArtifactError, 400),
    # deployment orchestration
    (DeploymentNotFoundError, 404),
    (UnsupportedDeploymentTargetError, 422),
    (DeploymentError, 400),
    # rollout engine
    (RolloutNotFoundError, 404),
    (UnsupportedRolloutStrategyError, 422),
    (RolloutError, 400),
    # feature flag platform
    (FeatureFlagNotFoundError, 404),
    (UnsupportedFeatureFlagScopeError, 422),
    (FeatureFlagError, 400),
    # update infrastructure
    (UpdateJobNotFoundError, 404),
    (UnsupportedUpdateTypeError, 422),
    (VersionCompatibilityError, 422),
    (UpdateError, 400),
    # license management
    (LicenseNotFoundError, 404),
    (LicenseExpiredError, 402),
    (SeatLimitExceededError, 422),
    (LicenseError, 400),
    # environment management
    (EnvironmentNotFoundError, 404),
    (UnsupportedEnvironmentTypeError, 422),
    (EnvironmentManagementError, 400),
    # deployment validation
    (HealthCheckFailedError, 422),
    (DeploymentValidationError, 400),
    # rollback engine
    (RollbackNotFoundError, 404),
    (UnsupportedRollbackTypeError, 422),
    (RollbackError, 400),
    # security & supply chain
    (SbomNotFoundError, 404),
    (SignatureVerificationFailedError, 422),
    (ChecksumMismatchError, 422),
    (ReleaseApprovalRequiredError, 422),
    (SupplyChainError, 400),
    # observability & release analytics
    (SnapshotNotFoundError, 404),
    (ReleaseAnalyticsError, 400),
    # common group
    (TenantIsolationError, 403),
    (PermissionDeniedError, 403),
    (AuthorizationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ValidationError, 422),
]


def _status_for(exc: ReleasePlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ReleasePlatformError)
    async def _handle_platform_error(request: Request, exc: ReleasePlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
