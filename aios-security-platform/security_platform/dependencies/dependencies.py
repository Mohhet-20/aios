"""FastAPI dependency wiring: DB session -> RepositoryRegistry -> every
service. Auth is intentionally minimal here, matching every sibling
AIOS platform: this platform expects to sit behind an already-
authenticated gateway (in practice, the Identity Platform) that
forwards the caller's tenant via `X-Tenant-Id` and, where relevant, the
acting principal via `X-User-Id`. Every service is built fresh per
request off a per-request `RepositoryRegistry`/`AsyncSession`, since a
session must never be shared across concurrent requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from security_platform.analytics.security_analytics_service import SecurityAnalyticsService
from security_platform.audit.audit_service import AuditService
from security_platform.compliance.compliance_service import ComplianceService
from security_platform.config.settings import Settings, get_settings
from security_platform.database.session import session_scope
from security_platform.dlp.dlp_service import DlpService
from security_platform.encryption.key_service import EncryptionKeyService
from security_platform.events.security_event_service import SecurityEventService
from security_platform.governance.approval_service import ApprovalWorkflowService
from security_platform.governance.governance_service import GovernanceAssetService
from security_platform.guardrails.guardrail_service import GuardrailService
from security_platform.guardrails.violation_service import GuardrailViolationService
from security_platform.pii.pii_service import PiiService
from security_platform.policies.evaluation_service import PolicyEvaluationService
from security_platform.policies.exception_service import PolicyExceptionService
from security_platform.policies.policy_service import PolicyService
from security_platform.repositories.registry import RepositoryRegistry
from security_platform.risk_engine.risk_service import RiskEngineService
from security_platform.secrets.access_service import SecretAccessService
from security_platform.secrets.secret_service import SecretService
from security_platform.threat_detection.threat_service import ThreatDetectionService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Delegates to `session_scope`, which commits on a clean exit and
    rolls back on any exception — a request handled through the REST
    API needs its writes to actually persist once the response is
    returned (see `database/session.py`'s docstring for the contrast
    with the bare, test-oriented `get_db_session`)."""
    async for session in session_scope():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session)) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
    return x_tenant_id


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str | None:
    """Unlike the tenant header, the actor header is optional — some
    of what this platform evaluates (automated guardrail checks,
    scheduled retention sweeps, system-triggered threat detection)
    legitimately comes from a process with no human actor behind it."""
    return x_user_id


# -- policy engine ---------------------------------------------------------------------
async def get_policy_service(repos: RepositoryRegistry = Depends(get_repos)) -> PolicyService:
    return PolicyService(repos)


async def get_policy_exception_service(repos: RepositoryRegistry = Depends(get_repos)) -> PolicyExceptionService:
    return PolicyExceptionService(repos)


async def get_policy_evaluation_service(repos: RepositoryRegistry = Depends(get_repos)) -> PolicyEvaluationService:
    return PolicyEvaluationService(repos)


# -- guardrails --------------------------------------------------------------------------
async def get_guardrail_service(repos: RepositoryRegistry = Depends(get_repos)) -> GuardrailService:
    return GuardrailService(repos)


async def get_guardrail_violation_service(repos: RepositoryRegistry = Depends(get_repos)) -> GuardrailViolationService:
    return GuardrailViolationService(repos)


# -- data protection: PII / DLP -----------------------------------------------------------
async def get_pii_service(repos: RepositoryRegistry = Depends(get_repos)) -> PiiService:
    return PiiService(repos)


async def get_dlp_service(repos: RepositoryRegistry = Depends(get_repos)) -> DlpService:
    return DlpService(repos)


# -- secrets / encryption -------------------------------------------------------------------
async def get_secret_service(repos: RepositoryRegistry = Depends(get_repos)) -> SecretService:
    return SecretService(repos)


async def get_secret_access_service(repos: RepositoryRegistry = Depends(get_repos)) -> SecretAccessService:
    return SecretAccessService(repos)


async def get_encryption_key_service(repos: RepositoryRegistry = Depends(get_repos)) -> EncryptionKeyService:
    return EncryptionKeyService(repos)


# -- risk engine -------------------------------------------------------------------------
async def get_risk_engine_service(repos: RepositoryRegistry = Depends(get_repos)) -> RiskEngineService:
    return RiskEngineService(repos)


# -- threat detection ---------------------------------------------------------------------
async def get_threat_detection_service(repos: RepositoryRegistry = Depends(get_repos)) -> ThreatDetectionService:
    return ThreatDetectionService(repos)


# -- governance --------------------------------------------------------------------------
async def get_governance_asset_service(repos: RepositoryRegistry = Depends(get_repos)) -> GovernanceAssetService:
    return GovernanceAssetService(repos)


async def get_approval_workflow_service(repos: RepositoryRegistry = Depends(get_repos)) -> ApprovalWorkflowService:
    return ApprovalWorkflowService(repos)


# -- security events / audit ---------------------------------------------------------------
async def get_security_event_service(repos: RepositoryRegistry = Depends(get_repos)) -> SecurityEventService:
    return SecurityEventService(repos)


async def get_audit_service(repos: RepositoryRegistry = Depends(get_repos)) -> AuditService:
    return AuditService(repos)


# -- compliance --------------------------------------------------------------------------
async def get_compliance_service(repos: RepositoryRegistry = Depends(get_repos)) -> ComplianceService:
    return ComplianceService(repos)


# -- analytics ---------------------------------------------------------------------------
async def get_security_analytics_service(repos: RepositoryRegistry = Depends(get_repos)) -> SecurityAnalyticsService:
    return SecurityAnalyticsService(repos)
