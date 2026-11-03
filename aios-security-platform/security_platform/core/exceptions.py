"""Exception hierarchy for the Enterprise Security, Guardrails & AI
Governance Platform."""
from __future__ import annotations


class SecurityPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(SecurityPlatformError):
    pass


class ValidationError(SecurityPlatformError):
    pass


class ConflictError(SecurityPlatformError):
    pass


class ConcurrentModificationError(SecurityPlatformError):
    pass


class AuthorizationError(SecurityPlatformError):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


class TenantIsolationError(AuthorizationError):
    pass


class InvalidTransitionError(SecurityPlatformError):
    """Raised on an illegal lifecycle transition (policy, secret,
    approval, incident-adjacent entities, etc.)."""


# -- guardrails ------------------------------------------------------------------

class GuardrailError(SecurityPlatformError):
    pass


class GuardrailViolationError(GuardrailError):
    """Raised when content is BLOCKED by a guardrail (as opposed to
    merely flagged) — callers that want to enforce blocking should
    catch this specifically."""


class PromptTooLongError(GuardrailError):
    pass


# -- data protection (PII / DLP) --------------------------------------------------

class DataProtectionError(SecurityPlatformError):
    pass


class DlpBlockError(DataProtectionError):
    """Raised when a DLP policy blocks an operation outright (critical
    severity finding on a block-configured policy)."""


# -- policy engine -----------------------------------------------------------------

class PolicyError(SecurityPlatformError):
    pass


class PolicyNotApplicableError(PolicyError):
    pass


class PolicyExceptionExpiredError(PolicyError):
    pass


# -- secrets / encryption ------------------------------------------------------------

class SecretError(SecurityPlatformError):
    pass


class SecretNotFoundError(SecretError):
    pass


class SecretExpiredError(SecretError):
    pass


class SecretAccessDeniedError(SecretError):
    pass


class EncryptionError(SecurityPlatformError):
    pass


class DecryptionError(EncryptionError):
    pass


class KeyRotationError(EncryptionError):
    pass


# -- risk engine -----------------------------------------------------------------------

class RiskEngineError(SecurityPlatformError):
    pass


# -- threat detection --------------------------------------------------------------------

class ThreatDetectionError(SecurityPlatformError):
    pass


# -- governance --------------------------------------------------------------------------

class GovernanceError(SecurityPlatformError):
    pass


class ApprovalError(GovernanceError):
    pass


class ApprovalAlreadyDecidedError(ApprovalError):
    pass


class OwnershipError(GovernanceError):
    pass


# -- security events / audit ----------------------------------------------------------------

class SecurityEventError(SecurityPlatformError):
    pass


class AuditLogError(SecurityPlatformError):
    pass


# -- compliance ----------------------------------------------------------------------------

class ComplianceError(SecurityPlatformError):
    pass


class LegalHoldActiveError(ComplianceError):
    """Raised when a deletion/retention action is attempted against
    data under an active legal hold."""


class RetentionPolicyError(ComplianceError):
    pass


class ConsentRequiredError(ComplianceError):
    pass


class DataResidencyViolationError(ComplianceError):
    pass
