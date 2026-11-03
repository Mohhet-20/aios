"""Maps the platform's domain exception hierarchy (core/exceptions.py)
to HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either. Order matters: this is checked top-to-bottom,
so subclasses are listed before their parent class."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from security_platform.core.exceptions import (
    ApprovalAlreadyDecidedError,
    ApprovalError,
    AuditLogError,
    AuthorizationError,
    ConcurrentModificationError,
    ConflictError,
    ComplianceError,
    ConsentRequiredError,
    DataProtectionError,
    DataResidencyViolationError,
    DecryptionError,
    DlpBlockError,
    EncryptionError,
    GovernanceError,
    GuardrailError,
    GuardrailViolationError,
    InvalidTransitionError,
    KeyRotationError,
    LegalHoldActiveError,
    NotFoundError,
    OwnershipError,
    PermissionDeniedError,
    PolicyError,
    PolicyExceptionExpiredError,
    PolicyNotApplicableError,
    PromptTooLongError,
    RetentionPolicyError,
    RiskEngineError,
    SecretAccessDeniedError,
    SecretError,
    SecretExpiredError,
    SecretNotFoundError,
    SecurityEventError,
    SecurityPlatformError,
    TenantIsolationError,
    ThreatDetectionError,
    ValidationError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[SecurityPlatformError], int]] = [
    (NotFoundError, 404),
    (SecretNotFoundError, 404),
    (SecretExpiredError, 410),
    (SecretAccessDeniedError, 403),
    (SecretError, 400),
    (DecryptionError, 400),
    (KeyRotationError, 400),
    (EncryptionError, 400),
    (GuardrailViolationError, 451),  # 451 Unavailable For Legal Reasons — blocked content
    (PromptTooLongError, 413),
    (GuardrailError, 400),
    (DlpBlockError, 451),
    (DataProtectionError, 400),
    (PolicyExceptionExpiredError, 410),
    (PolicyNotApplicableError, 422),
    (PolicyError, 400),
    (RiskEngineError, 400),
    (ThreatDetectionError, 400),
    (ApprovalAlreadyDecidedError, 409),
    (ApprovalError, 400),
    (OwnershipError, 400),
    (GovernanceError, 400),
    (SecurityEventError, 400),
    (AuditLogError, 400),
    (LegalHoldActiveError, 423),  # 423 Locked
    (ConsentRequiredError, 403),
    (DataResidencyViolationError, 451),
    (RetentionPolicyError, 400),
    (ComplianceError, 400),
    (TenantIsolationError, 403),
    (PermissionDeniedError, 403),
    (AuthorizationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ValidationError, 422),
]


def _status_for(exc: SecurityPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(SecurityPlatformError)
    async def _handle_platform_error(request: Request, exc: SecurityPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
