"""Domain exception hierarchy. Every service raises these directly —
the REST layer's exception_handlers.py maps them to HTTP status codes
so no router needs a try/except block."""
from __future__ import annotations


class ReleasePlatformError(Exception):
    pass


# -- common ---------------------------------------------------------------------------------------------

class NotFoundError(ReleasePlatformError):
    pass


class ValidationError(ReleasePlatformError):
    pass


class ConflictError(ReleasePlatformError):
    pass


class ConcurrentModificationError(ReleasePlatformError):
    pass


class AuthorizationError(ReleasePlatformError):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


class TenantIsolationError(AuthorizationError):
    pass


class InvalidTransitionError(ReleasePlatformError):
    pass


# -- release & version management -------------------------------------------------------------------------

class ReleaseError(ReleasePlatformError):
    pass


class ReleaseNotFoundError(ReleaseError):
    pass


class VersionNotFoundError(ReleaseError):
    pass


class UnsupportedReleaseChannelError(ReleaseError):
    pass


class IncompatibleVersionError(ReleaseError):
    pass


# -- artifact management & enterprise distribution ---------------------------------------------------------

class ArtifactError(ReleasePlatformError):
    pass


class ArtifactNotFoundError(ArtifactError):
    pass


class UnsupportedArtifactTypeError(ArtifactError):
    pass


class DistributionChannelNotFoundError(ArtifactError):
    pass


# -- deployment orchestration ------------------------------------------------------------------------------

class DeploymentError(ReleasePlatformError):
    pass


class DeploymentNotFoundError(DeploymentError):
    pass


class UnsupportedDeploymentTargetError(DeploymentError):
    pass


# -- rollout engine -----------------------------------------------------------------------------------------

class RolloutError(ReleasePlatformError):
    pass


class RolloutNotFoundError(RolloutError):
    pass


class UnsupportedRolloutStrategyError(RolloutError):
    pass


# -- feature flag platform ------------------------------------------------------------------------------------

class FeatureFlagError(ReleasePlatformError):
    pass


class FeatureFlagNotFoundError(FeatureFlagError):
    pass


class UnsupportedFeatureFlagScopeError(FeatureFlagError):
    pass


# -- update infrastructure ------------------------------------------------------------------------------------

class UpdateError(ReleasePlatformError):
    pass


class UpdateJobNotFoundError(UpdateError):
    pass


class UnsupportedUpdateTypeError(UpdateError):
    pass


class VersionCompatibilityError(UpdateError):
    pass


# -- license management ------------------------------------------------------------------------------------------

class LicenseError(ReleasePlatformError):
    pass


class LicenseNotFoundError(LicenseError):
    pass


class LicenseExpiredError(LicenseError):
    pass


class SeatLimitExceededError(LicenseError):
    pass


# -- environment management ------------------------------------------------------------------------------------------

class EnvironmentManagementError(ReleasePlatformError):
    pass


class EnvironmentNotFoundError(EnvironmentManagementError):
    pass


class UnsupportedEnvironmentTypeError(EnvironmentManagementError):
    pass


# -- deployment validation & rollback engine -----------------------------------------------------------------------

class DeploymentValidationError(ReleasePlatformError):
    pass


class HealthCheckFailedError(DeploymentValidationError):
    pass


class RollbackError(ReleasePlatformError):
    pass


class RollbackNotFoundError(RollbackError):
    pass


class UnsupportedRollbackTypeError(RollbackError):
    pass


# -- security & supply chain -----------------------------------------------------------------------------------------

class SupplyChainError(ReleasePlatformError):
    pass


class SignatureVerificationFailedError(SupplyChainError):
    pass


class SbomNotFoundError(SupplyChainError):
    pass


class ChecksumMismatchError(SupplyChainError):
    pass


class ReleaseApprovalRequiredError(SupplyChainError):
    pass


# -- observability & release analytics -----------------------------------------------------------------------------------------

class ReleaseAnalyticsError(ReleasePlatformError):
    pass


class SnapshotNotFoundError(ReleaseAnalyticsError):
    pass
