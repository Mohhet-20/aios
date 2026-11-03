"""Enumerations for the Enterprise Authentication, Organizations &
Multi-Tenant Platform — every enum here mirrors a real column value or
a real business-rule branch, never speculative."""
from __future__ import annotations

from enum import Enum


class UserStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    LOCKED = "locked"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class TenantTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class WorkspaceStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class TeamStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class DepartmentUnitType(str, Enum):
    DEPARTMENT = "department"
    BUSINESS_UNIT = "business_unit"


class MembershipStatus(str, Enum):
    ACTIVE = "active"
    INVITED = "invited"
    REMOVED = "removed"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"

    @classmethod
    def terminal(cls) -> set["SessionStatus"]:
        return {cls.REVOKED, cls.EXPIRED}


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ApiKeyStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ServiceAccountStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class MfaFactorType(str, Enum):
    TOTP = "totp"


class MfaFactorStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DISABLED = "disabled"


class RoleScopeType(str, Enum):
    SYSTEM = "system"
    ORGANIZATION = "organization"
    WORKSPACE = "workspace"
    PROJECT = "project"


class PrincipalType(str, Enum):
    USER = "user"
    SERVICE_ACCOUNT = "service_account"
    GROUP = "group"


class PermissionResourceType(str, Enum):
    ORGANIZATION = "organization"
    WORKSPACE = "workspace"
    TEAM = "team"
    PROJECT = "project"
    USER = "user"
    ROLE = "role"
    API_KEY = "api_key"
    AGENT = "agent"
    WORKFLOW = "workflow"
    PROMPT = "prompt"
    TOOL = "tool"
    MEMORY = "memory"
    DATASET = "dataset"
    SECURITY = "security"
    AUDIT = "audit"


class PermissionAction(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    MANAGE = "manage"
    INVITE = "invite"
    APPROVE = "approve"


class IdentityProviderKey(str, Enum):
    PASSWORD = "password"
    GOOGLE = "google"
    GITHUB = "github"
    AZURE_AD = "azure_ad"
    GENERIC_OIDC = "generic_oidc"
    SAML = "saml"


class SecurityPolicyType(str, Enum):
    PASSWORD = "password"
    SESSION = "session"
    IP_RESTRICTION = "ip_restriction"
    GEO_RESTRICTION = "geo_restriction"
    MFA_REQUIREMENT = "mfa_requirement"
    RETENTION = "retention"
    APPROVAL = "approval"


class SecurityEventType(str, Enum):
    BRUTE_FORCE = "brute_force"
    ANOMALY = "anomaly"
    ACCOUNT_LOCKOUT = "account_lockout"
    SUSPICIOUS_LOGIN = "suspicious_login"
    IP_BLOCKED = "ip_blocked"
    GEO_BLOCKED = "geo_blocked"


class SecurityEventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AuditActorType(str, Enum):
    USER = "user"
    SERVICE_ACCOUNT = "service_account"
    SYSTEM = "system"
