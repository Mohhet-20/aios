"""Importing this package populates `Base.metadata` with every ORM
model — required once at process/test startup before `init_models()`."""
from identity_platform.models.api_key import ApiKeyModel, ServiceAccountModel, WebhookSecretModel
from identity_platform.models.credentials import (
    EmailVerificationTokenModel,
    MagicLinkTokenModel,
    PasswordCredentialModel,
    PasswordResetTokenModel,
)
from identity_platform.models.federated import ExternalIdentityModel
from identity_platform.models.governance import AuditLogEntryModel
from identity_platform.models.group import GroupModel
from identity_platform.models.invitation import InvitationModel
from identity_platform.models.membership import (
    GroupMembershipModel,
    OrganizationMembershipModel,
    ProjectMembershipModel,
    TeamMembershipModel,
    WorkspaceMembershipModel,
)
from identity_platform.models.mfa import MfaFactorModel, RecoveryCodeModel, TrustedDeviceModel
from identity_platform.models.organization import DepartmentModel, OrganizationModel
from identity_platform.models.project import ProjectModel
from identity_platform.models.rbac import PermissionModel, RoleAssignmentModel, RoleModel
from identity_platform.models.security import SecurityEventModel, SecurityPolicyModel
from identity_platform.models.session import LoginHistoryModel, SessionModel
from identity_platform.models.team import TeamModel
from identity_platform.models.user import UserModel
from identity_platform.models.workspace import WorkspaceModel

__all__ = [
    "ApiKeyModel",
    "AuditLogEntryModel",
    "DepartmentModel",
    "EmailVerificationTokenModel",
    "ExternalIdentityModel",
    "GroupMembershipModel",
    "GroupModel",
    "InvitationModel",
    "LoginHistoryModel",
    "MagicLinkTokenModel",
    "MfaFactorModel",
    "OrganizationMembershipModel",
    "OrganizationModel",
    "PasswordCredentialModel",
    "PasswordResetTokenModel",
    "PermissionModel",
    "ProjectMembershipModel",
    "ProjectModel",
    "RecoveryCodeModel",
    "RoleAssignmentModel",
    "RoleModel",
    "SecurityEventModel",
    "SecurityPolicyModel",
    "ServiceAccountModel",
    "SessionModel",
    "TeamMembershipModel",
    "TeamModel",
    "TrustedDeviceModel",
    "UserModel",
    "WebhookSecretModel",
    "WorkspaceMembershipModel",
    "WorkspaceModel",
]
