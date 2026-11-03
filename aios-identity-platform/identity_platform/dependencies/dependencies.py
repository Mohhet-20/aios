"""FastAPI dependency wiring: DB session -> RepositoryRegistry -> every
service. Auth is intentionally minimal here, matching every sibling
AIOS platform: this platform expects to sit behind an already-
authenticated gateway that forwards the caller's identity via the
`X-User-Id` header (this platform IS the identity provider for every
other AIOS platform, but its own REST layer still needs a caller-
identity seam for endpoints like "who is making this request" audit
fields). Every service is built fresh per request off a per-request
`RepositoryRegistry`/`AsyncSession`, since a session must never be
shared across concurrent requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from identity_platform.api_keys.api_key_service import ApiKeyService
from identity_platform.api_keys.service_account_service import ServiceAccountService
from identity_platform.api_keys.webhook_secret_service import WebhookSecretService
from identity_platform.authentication.email_verification_service import EmailVerificationService
from identity_platform.authentication.login_service import LoginService
from identity_platform.authentication.magic_link_service import MagicLinkService
from identity_platform.authentication.password_service import PasswordService
from identity_platform.authentication.registration_service import RegistrationService
from identity_platform.authorization.assignment_service import RoleAssignmentService
from identity_platform.authorization.authorization_service import AuthorizationService
from identity_platform.authorization.role_service import RoleService
from identity_platform.config.settings import Settings, get_settings
from identity_platform.database.session import session_scope
from identity_platform.federated.federated_identity_service import FederatedIdentityService
from identity_platform.governance.audit_service import AuditService
from identity_platform.governance.compliance_service import ComplianceService
from identity_platform.governance.retention_service import RetentionService
from identity_platform.mfa.device_trust_service import DeviceTrustService
from identity_platform.mfa.mfa_service import MfaService
from identity_platform.observability.metrics_service import ObservabilityMetricsService
from identity_platform.organizations.group_service import GroupService
from identity_platform.organizations.invitation_service import InvitationService
from identity_platform.organizations.membership_service import MembershipService
from identity_platform.organizations.organization_service import OrganizationService
from identity_platform.organizations.project_service import ProjectService
from identity_platform.organizations.team_service import TeamService
from identity_platform.organizations.workspace_service import WorkspaceService
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security_platform.account_recovery_service import AccountRecoveryService
from identity_platform.security_platform.policy_service import SecurityPolicyService
from identity_platform.security_platform.rate_limit_service import RateLimitService, get_default_rate_limiter
from identity_platform.security_platform.restriction_service import RestrictionService
from identity_platform.security_platform.risk_service import RiskScoringService
from identity_platform.security_platform.security_event_service import SecurityEventService
from identity_platform.sessions.jwt_service import JwtService
from identity_platform.sessions.session_service import SessionService
from identity_platform.tenancy.tier_service import TenantTierService
from identity_platform.tenancy.usage_service import TenantUsageService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Delegates to `session_scope`, which commits on a clean exit and
    rolls back on any exception — unlike the bare `get_db_session`
    generator (which neither commits nor rolls back and is meant for
    callers that manage their own transaction boundary, e.g. tests),
    a request handled through the REST API needs its writes to
    actually persist once the response is returned."""
    async for session in session_scope():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session)) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id


# -- authentication ----------------------------------------------------------------

def get_registration_service(repos: RepositoryRegistry = Depends(get_repos)) -> RegistrationService:
    return RegistrationService(repos)


def get_email_verification_service(repos: RepositoryRegistry = Depends(get_repos)) -> EmailVerificationService:
    return EmailVerificationService(repos)


def get_login_service(repos: RepositoryRegistry = Depends(get_repos)) -> LoginService:
    return LoginService(repos)


def get_password_service(repos: RepositoryRegistry = Depends(get_repos)) -> PasswordService:
    return PasswordService(repos)


def get_magic_link_service(repos: RepositoryRegistry = Depends(get_repos)) -> MagicLinkService:
    return MagicLinkService(repos)


# -- MFA / device trust ----------------------------------------------------------

def get_mfa_service(repos: RepositoryRegistry = Depends(get_repos)) -> MfaService:
    return MfaService(repos)


def get_device_trust_service(repos: RepositoryRegistry = Depends(get_repos)) -> DeviceTrustService:
    return DeviceTrustService(repos)


# -- sessions ---------------------------------------------------------------------

def get_session_service(repos: RepositoryRegistry = Depends(get_repos)) -> SessionService:
    return SessionService(repos)


def get_jwt_service() -> JwtService:
    return JwtService()


# -- federated identity -------------------------------------------------------------

def get_federated_identity_service(repos: RepositoryRegistry = Depends(get_repos)) -> FederatedIdentityService:
    return FederatedIdentityService(repos)


# -- authorization ------------------------------------------------------------------

def get_role_service(repos: RepositoryRegistry = Depends(get_repos)) -> RoleService:
    return RoleService(repos)


def get_role_assignment_service(repos: RepositoryRegistry = Depends(get_repos)) -> RoleAssignmentService:
    return RoleAssignmentService(repos)


def get_authorization_service(repos: RepositoryRegistry = Depends(get_repos)) -> AuthorizationService:
    return AuthorizationService(repos)


# -- organizations / workspaces / teams / projects / groups ----------------------------

def get_organization_service(repos: RepositoryRegistry = Depends(get_repos)) -> OrganizationService:
    return OrganizationService(repos)


def get_workspace_service(repos: RepositoryRegistry = Depends(get_repos)) -> WorkspaceService:
    return WorkspaceService(repos)


def get_team_service(repos: RepositoryRegistry = Depends(get_repos)) -> TeamService:
    return TeamService(repos)


def get_project_service(repos: RepositoryRegistry = Depends(get_repos)) -> ProjectService:
    return ProjectService(repos)


def get_group_service(repos: RepositoryRegistry = Depends(get_repos)) -> GroupService:
    return GroupService(repos)


def get_membership_service(repos: RepositoryRegistry = Depends(get_repos)) -> MembershipService:
    return MembershipService(repos)


def get_invitation_service(repos: RepositoryRegistry = Depends(get_repos)) -> InvitationService:
    return InvitationService(repos)


# -- multi-tenancy -------------------------------------------------------------------

def get_tenant_usage_service(repos: RepositoryRegistry = Depends(get_repos)) -> TenantUsageService:
    return TenantUsageService(repos)


def get_tenant_tier_service(repos: RepositoryRegistry = Depends(get_repos)) -> TenantTierService:
    return TenantTierService(repos)


# -- API keys / service accounts -----------------------------------------------------

def get_api_key_service(repos: RepositoryRegistry = Depends(get_repos)) -> ApiKeyService:
    return ApiKeyService(repos)


def get_service_account_service(repos: RepositoryRegistry = Depends(get_repos)) -> ServiceAccountService:
    return ServiceAccountService(repos)


def get_webhook_secret_service(repos: RepositoryRegistry = Depends(get_repos)) -> WebhookSecretService:
    return WebhookSecretService(repos)


# -- security platform ----------------------------------------------------------------

def get_security_policy_service(repos: RepositoryRegistry = Depends(get_repos)) -> SecurityPolicyService:
    return SecurityPolicyService(repos)


def get_security_event_service(repos: RepositoryRegistry = Depends(get_repos)) -> SecurityEventService:
    return SecurityEventService(repos)


def get_rate_limit_service() -> RateLimitService:
    return get_default_rate_limiter()


def get_restriction_service(repos: RepositoryRegistry = Depends(get_repos)) -> RestrictionService:
    return RestrictionService(repos)


def get_risk_scoring_service(repos: RepositoryRegistry = Depends(get_repos)) -> RiskScoringService:
    return RiskScoringService(repos)


def get_account_recovery_service(repos: RepositoryRegistry = Depends(get_repos)) -> AccountRecoveryService:
    return AccountRecoveryService(repos)


# -- governance ------------------------------------------------------------------------

def get_audit_service(repos: RepositoryRegistry = Depends(get_repos)) -> AuditService:
    return AuditService(repos)


def get_retention_service(repos: RepositoryRegistry = Depends(get_repos)) -> RetentionService:
    return RetentionService(repos)


def get_compliance_service(repos: RepositoryRegistry = Depends(get_repos)) -> ComplianceService:
    return ComplianceService(repos)


# -- observability -----------------------------------------------------------------------

def get_observability_metrics_service(repos: RepositoryRegistry = Depends(get_repos)) -> ObservabilityMetricsService:
    return ObservabilityMetricsService(repos)
