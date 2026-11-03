"""Exception hierarchy for the Enterprise Authentication, Organizations
& Multi-Tenant Platform."""
from __future__ import annotations


class IdentityPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(IdentityPlatformError):
    pass


class ValidationError(IdentityPlatformError):
    pass


class ConflictError(IdentityPlatformError):
    pass


class ConcurrentModificationError(IdentityPlatformError):
    pass


class AuthorizationError(IdentityPlatformError):
    pass


class InvalidTransitionError(IdentityPlatformError):
    """Raised on an illegal user/session/invitation/api-key lifecycle transition."""


# -- authentication ----------------------------------------------------------------

class AuthenticationError(IdentityPlatformError):
    pass


class InvalidCredentialsError(AuthenticationError):
    pass


class AccountLockedError(AuthenticationError):
    pass


class AccountNotVerifiedError(AuthenticationError):
    pass


class PasswordPolicyError(ValidationError):
    pass


class TokenError(AuthenticationError):
    pass


class TokenExpiredError(TokenError):
    pass


class TokenAlreadyUsedError(TokenError):
    pass


# -- MFA -----------------------------------------------------------------------------

class MfaError(AuthenticationError):
    pass


class MfaRequiredError(MfaError):
    pass


class InvalidMfaCodeError(MfaError):
    pass


class RecoveryCodeExhaustedError(MfaError):
    pass


# -- sessions --------------------------------------------------------------------------

class SessionError(IdentityPlatformError):
    pass


class SessionExpiredError(SessionError):
    pass


class SessionRevokedError(SessionError):
    pass


class ConcurrentSessionLimitExceededError(SessionError):
    pass


# -- federated identity ------------------------------------------------------------------

class FederatedIdentityError(IdentityPlatformError):
    pass


class UnknownIdentityProviderError(FederatedIdentityError):
    pass


# -- organizations / workspaces / teams / projects -----------------------------------------

class OrganizationError(IdentityPlatformError):
    pass


class WorkspaceError(IdentityPlatformError):
    pass


class TeamError(IdentityPlatformError):
    pass


class ProjectError(IdentityPlatformError):
    pass


class InvitationError(IdentityPlatformError):
    pass


class InvitationExpiredError(InvitationError):
    pass


class MembershipError(IdentityPlatformError):
    pass


# -- RBAC / permissions -----------------------------------------------------------------

class RoleError(IdentityPlatformError):
    pass


class UnknownPermissionError(IdentityPlatformError):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


# -- multi-tenancy -----------------------------------------------------------------------

class TenantIsolationError(IdentityPlatformError):
    """Raised when a request would let one tenant/organization/workspace
    read or write another's data — always a hard stop, never a warning."""


class QuotaExceededError(IdentityPlatformError):
    pass


# -- API keys / service accounts -----------------------------------------------------------

class ApiKeyError(IdentityPlatformError):
    pass


class ApiKeyExpiredError(ApiKeyError):
    pass


class ApiKeyRevokedError(ApiKeyError):
    pass


class ServiceAccountError(IdentityPlatformError):
    pass


# -- security --------------------------------------------------------------------------

class RateLimitExceededError(IdentityPlatformError):
    pass


class IpRestrictedError(AuthorizationError):
    pass


class GeoRestrictedError(AuthorizationError):
    pass


class AnomalyDetectedError(IdentityPlatformError):
    """Raised (informationally) when a login/action is scored high-risk
    and blocked pending additional verification."""


# -- governance ------------------------------------------------------------------------

class PolicyError(IdentityPlatformError):
    pass
