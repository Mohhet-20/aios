"""RepositoryRegistry: wires every repository to one shared AsyncSession,
so a single unit-of-work-scoped session backs every repository an
application-service call touches. Same pattern as every other AIOS
services's `RepositoryRegistry`."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from identity_platform.repositories.api_key_repository import (
    ApiKeyRepository,
    ServiceAccountRepository,
    WebhookSecretRepository,
)
from identity_platform.repositories.credential_repository import (
    EmailVerificationTokenRepository,
    MagicLinkTokenRepository,
    PasswordCredentialRepository,
    PasswordResetTokenRepository,
)
from identity_platform.repositories.federated_repository import ExternalIdentityRepository
from identity_platform.repositories.governance_repository import AuditLogEntryRepository
from identity_platform.repositories.group_repository import GroupRepository
from identity_platform.repositories.invitation_repository import InvitationRepository
from identity_platform.repositories.membership_repository import (
    GroupMembershipRepository,
    OrganizationMembershipRepository,
    ProjectMembershipRepository,
    TeamMembershipRepository,
    WorkspaceMembershipRepository,
)
from identity_platform.repositories.mfa_repository import (
    MfaFactorRepository,
    RecoveryCodeRepository,
    TrustedDeviceRepository,
)
from identity_platform.repositories.organization_repository import DepartmentRepository, OrganizationRepository
from identity_platform.repositories.project_repository import ProjectRepository
from identity_platform.repositories.rbac_repository import (
    PermissionRepository,
    RoleAssignmentRepository,
    RoleRepository,
)
from identity_platform.repositories.security_repository import SecurityEventRepository, SecurityPolicyRepository
from identity_platform.repositories.session_repository import LoginHistoryRepository, SessionRepository
from identity_platform.repositories.team_repository import TeamRepository
from identity_platform.repositories.user_repository import UserRepository
from identity_platform.repositories.workspace_repository import WorkspaceRepository


class RepositoryRegistry:
    """One instance per unit-of-work session; exposes every repository as
    a lazily-constructed, memoized property so services only pay for the
    repositories they actually touch."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[str, object] = {}

    def _get(self, key: str, cls: type):
        if key not in self._cache:
            self._cache[key] = cls(self.session)
        return self._cache[key]

    # -- identity core --------------------------------------------------
    @property
    def users(self) -> UserRepository:
        return self._get("users", UserRepository)

    @property
    def password_credentials(self) -> PasswordCredentialRepository:
        return self._get("password_credentials", PasswordCredentialRepository)

    @property
    def email_verification_tokens(self) -> EmailVerificationTokenRepository:
        return self._get("email_verification_tokens", EmailVerificationTokenRepository)

    @property
    def password_reset_tokens(self) -> PasswordResetTokenRepository:
        return self._get("password_reset_tokens", PasswordResetTokenRepository)

    @property
    def magic_link_tokens(self) -> MagicLinkTokenRepository:
        return self._get("magic_link_tokens", MagicLinkTokenRepository)

    # -- MFA / device trust ----------------------------------------------
    @property
    def mfa_factors(self) -> MfaFactorRepository:
        return self._get("mfa_factors", MfaFactorRepository)

    @property
    def recovery_codes(self) -> RecoveryCodeRepository:
        return self._get("recovery_codes", RecoveryCodeRepository)

    @property
    def trusted_devices(self) -> TrustedDeviceRepository:
        return self._get("trusted_devices", TrustedDeviceRepository)

    # -- sessions ---------------------------------------------------------
    @property
    def sessions(self) -> SessionRepository:
        return self._get("sessions", SessionRepository)

    @property
    def login_history(self) -> LoginHistoryRepository:
        return self._get("login_history", LoginHistoryRepository)

    # -- federated identity -----------------------------------------------
    @property
    def external_identities(self) -> ExternalIdentityRepository:
        return self._get("external_identities", ExternalIdentityRepository)

    # -- tenancy hierarchy --------------------------------------------------
    @property
    def organizations(self) -> OrganizationRepository:
        return self._get("organizations", OrganizationRepository)

    @property
    def departments(self) -> DepartmentRepository:
        return self._get("departments", DepartmentRepository)

    @property
    def workspaces(self) -> WorkspaceRepository:
        return self._get("workspaces", WorkspaceRepository)

    @property
    def teams(self) -> TeamRepository:
        return self._get("teams", TeamRepository)

    @property
    def projects(self) -> ProjectRepository:
        return self._get("projects", ProjectRepository)

    @property
    def groups(self) -> GroupRepository:
        return self._get("groups", GroupRepository)

    # -- memberships -----------------------------------------------------
    @property
    def organization_memberships(self) -> OrganizationMembershipRepository:
        return self._get("organization_memberships", OrganizationMembershipRepository)

    @property
    def workspace_memberships(self) -> WorkspaceMembershipRepository:
        return self._get("workspace_memberships", WorkspaceMembershipRepository)

    @property
    def team_memberships(self) -> TeamMembershipRepository:
        return self._get("team_memberships", TeamMembershipRepository)

    @property
    def project_memberships(self) -> ProjectMembershipRepository:
        return self._get("project_memberships", ProjectMembershipRepository)

    @property
    def group_memberships(self) -> GroupMembershipRepository:
        return self._get("group_memberships", GroupMembershipRepository)

    # -- RBAC --------------------------------------------------------------
    @property
    def roles(self) -> RoleRepository:
        return self._get("roles", RoleRepository)

    @property
    def role_assignments(self) -> RoleAssignmentRepository:
        return self._get("role_assignments", RoleAssignmentRepository)

    @property
    def permissions(self) -> PermissionRepository:
        return self._get("permissions", PermissionRepository)

    # -- invitations --------------------------------------------------------
    @property
    def invitations(self) -> InvitationRepository:
        return self._get("invitations", InvitationRepository)

    # -- API keys / service accounts ----------------------------------------
    @property
    def api_keys(self) -> ApiKeyRepository:
        return self._get("api_keys", ApiKeyRepository)

    @property
    def service_accounts(self) -> ServiceAccountRepository:
        return self._get("service_accounts", ServiceAccountRepository)

    @property
    def webhook_secrets(self) -> WebhookSecretRepository:
        return self._get("webhook_secrets", WebhookSecretRepository)

    # -- security -------------------------------------------------------------
    @property
    def security_policies(self) -> SecurityPolicyRepository:
        return self._get("security_policies", SecurityPolicyRepository)

    @property
    def security_events(self) -> SecurityEventRepository:
        return self._get("security_events", SecurityEventRepository)

    # -- governance -------------------------------------------------------------
    @property
    def audit_log_entries(self) -> AuditLogEntryRepository:
        return self._get("audit_log_entries", AuditLogEntryRepository)
