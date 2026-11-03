"""Enumerations shared across the domain, ORM, and service layers."""
from __future__ import annotations

import enum


class PolicyScope(str, enum.Enum):
    ORGANIZATION = "organization"
    WORKSPACE = "workspace"
    PROJECT = "project"
    AGENT = "agent"
    PROMPT = "prompt"
    WORKFLOW = "workflow"
    TOOL = "tool"
    MEMORY = "memory"
    MODEL = "model"
    DATASET = "dataset"

    @property
    def rank(self) -> int:
        """Broadest to narrowest — used to resolve inheritance
        (a narrower scope's policy overrides a broader one for the
        same subject, most-specific-wins)."""
        order = [
            PolicyScope.ORGANIZATION, PolicyScope.WORKSPACE, PolicyScope.PROJECT,
            PolicyScope.AGENT, PolicyScope.PROMPT, PolicyScope.WORKFLOW,
            PolicyScope.TOOL, PolicyScope.MEMORY, PolicyScope.MODEL, PolicyScope.DATASET,
        ]
        return order.index(self)


class PolicyStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class PolicyEffect(str, enum.Enum):
    ALLOW = "allow"
    DENY = "deny"
    FLAG = "flag"


class GuardrailCategory(str, enum.Enum):
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    INDIRECT_PROMPT_INJECTION = "indirect_prompt_injection"
    UNSAFE_INSTRUCTION = "unsafe_instruction"
    POLICY_VIOLATION = "policy_violation"
    TOOL_MISUSE = "tool_misuse"
    UNSAFE_AGENT_BEHAVIOR = "unsafe_agent_behavior"
    UNSAFE_WORKFLOW = "unsafe_workflow"
    OUTPUT_VALIDATION = "output_validation"
    STRUCTURED_OUTPUT_VALIDATION = "structured_output_validation"
    RESPONSE_FILTER = "response_filter"


class GuardrailAction(str, enum.Enum):
    ALLOW = "allow"
    FLAG = "flag"
    BLOCK = "block"
    REDACT = "redact"


class ViolationStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class PiiEntityType(str, enum.Enum):
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    NAME = "name"
    ADDRESS = "address"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    BANK_ACCOUNT = "bank_account"
    MEDICAL_RECORD = "medical_record"
    CUSTOM = "custom"


class DataSensitivity(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

    @property
    def rank(self) -> int:
        return {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}[self.value]


class DlpSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return {"low": 0, "medium": 1, "high": 2, "critical": 3}[self.value]


class DlpAction(str, enum.Enum):
    ALLOW = "allow"
    FLAG = "flag"
    REDACT = "redact"
    BLOCK = "block"


class SecretType(str, enum.Enum):
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    ENCRYPTION_KEY = "encryption_key"
    CERTIFICATE = "certificate"
    CONNECTION_STRING = "connection_string"
    CUSTOM = "custom"


class SecretStatus(str, enum.Enum):
    ACTIVE = "active"
    ROTATING = "rotating"
    EXPIRED = "expired"
    REVOKED = "revoked"


class RiskEntityType(str, enum.Enum):
    USER = "user"
    SESSION = "session"
    WORKFLOW = "workflow"
    PROMPT = "prompt"
    AGENT = "agent"
    TOOL = "tool"
    DATA = "data"
    ORGANIZATION = "organization"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(str, enum.Enum):
    ANOMALY = "anomaly"
    BEHAVIOR = "behavior"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    CREDENTIAL_ABUSE = "credential_abuse"
    API_ABUSE = "api_abuse"
    BRUTE_FORCE = "brute_force"
    SUSPICIOUS_WORKFLOW = "suspicious_workflow"
    MALICIOUS_PROMPT = "malicious_prompt"
    TOOL_ABUSE = "tool_abuse"


class ThreatSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatStatus(str, enum.Enum):
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    MITIGATED = "mitigated"


class GovernanceAssetType(str, enum.Enum):
    MODEL = "model"
    PROMPT = "prompt"
    WORKFLOW = "workflow"
    DATASET = "dataset"
    AGENT = "agent"
    KNOWLEDGE = "knowledge"


class LifecycleStage(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class SecurityEventType(str, enum.Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    POLICY_VIOLATION = "policy_violation"
    PROMPT_VIOLATION = "prompt_violation"
    TOOL_VIOLATION = "tool_violation"
    WORKFLOW_VIOLATION = "workflow_violation"
    SECRETS_ACCESS = "secrets_access"
    RISK_CHANGE = "risk_change"
    THREAT_DETECTION = "threat_detection"
    ADMINISTRATIVE_ACTION = "administrative_action"


class SecurityEventSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceFramework(str, enum.Enum):
    GDPR = "gdpr"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    HIPAA = "hipaa"
    CUSTOM = "custom"


class LegalHoldStatus(str, enum.Enum):
    ACTIVE = "active"
    RELEASED = "released"


class ConsentStatus(str, enum.Enum):
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class SecurityRole(str, enum.Enum):
    """Ordered — deliberately smaller than the Identity Platform's
    fine-grained resource_type:action grammar, matching the precedent
    set by the Observability Platform's `ObservabilityRole`. This
    platform only needs to answer "can this principal view security
    posture / operate on policies & guardrails & secrets / administer
    the whole platform"."""
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"

    @property
    def rank(self) -> int:
        return {"viewer": 0, "operator": 1, "admin": 2}[self.value]


def role_at_least(role: SecurityRole, minimum: SecurityRole) -> bool:
    return role.rank >= minimum.rank
