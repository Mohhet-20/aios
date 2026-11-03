"""RepositoryRegistry: wires every repository to one shared AsyncSession,
so a single unit-of-work-scoped session backs every repository an
application-service call touches. Same pattern as every prior AIOS
platform's `RepositoryRegistry`."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from security_platform.repositories.compliance_repository import (
    ComplianceEvidenceRepository,
    ComplianceFrameworkConfigRepository,
    ConsentRecordRepository,
    DataResidencyRecordRepository,
    LegalHoldRepository,
    RetentionPolicyRepository,
)
from security_platform.repositories.data_protection_repository import (
    DataClassificationRepository,
    DlpIncidentRepository,
    DlpPolicyRepository,
    PiiFindingRepository,
)
from security_platform.repositories.events_repository import AuditLogEntryRepository, SecurityEventRepository
from security_platform.repositories.governance_repository import (
    ApprovalDecisionRepository,
    ApprovalPolicyRepository,
    ApprovalRequestRepository,
    GovernanceAssetRepository,
)
from security_platform.repositories.guardrail_repository import (
    GuardrailEvaluationRepository,
    GuardrailRuleRepository,
    GuardrailViolationRepository,
)
from security_platform.repositories.policy_repository import PolicyExceptionRepository, PolicyRepository, PolicyVersionRepository
from security_platform.repositories.risk_repository import RiskScoreRepository
from security_platform.repositories.secret_repository import (
    EncryptionKeyRepository,
    SecretAccessLogRepository,
    SecretAccessPolicyRepository,
    SecretRepository,
    SecretVersionRepository,
)
from security_platform.repositories.threat_repository import ThreatDetectionRepository


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

    # -- policies -------------------------------------------------------------------
    @property
    def policies(self) -> PolicyRepository:
        return self._get("policies", PolicyRepository)

    @property
    def policy_versions(self) -> PolicyVersionRepository:
        return self._get("policy_versions", PolicyVersionRepository)

    @property
    def policy_exceptions(self) -> PolicyExceptionRepository:
        return self._get("policy_exceptions", PolicyExceptionRepository)

    # -- guardrails -------------------------------------------------------------------
    @property
    def guardrail_rules(self) -> GuardrailRuleRepository:
        return self._get("guardrail_rules", GuardrailRuleRepository)

    @property
    def guardrail_evaluations(self) -> GuardrailEvaluationRepository:
        return self._get("guardrail_evaluations", GuardrailEvaluationRepository)

    @property
    def guardrail_violations(self) -> GuardrailViolationRepository:
        return self._get("guardrail_violations", GuardrailViolationRepository)

    # -- data protection ----------------------------------------------------------------
    @property
    def pii_findings(self) -> PiiFindingRepository:
        return self._get("pii_findings", PiiFindingRepository)

    @property
    def data_classifications(self) -> DataClassificationRepository:
        return self._get("data_classifications", DataClassificationRepository)

    @property
    def dlp_policies(self) -> DlpPolicyRepository:
        return self._get("dlp_policies", DlpPolicyRepository)

    @property
    def dlp_incidents(self) -> DlpIncidentRepository:
        return self._get("dlp_incidents", DlpIncidentRepository)

    # -- secrets / encryption ------------------------------------------------------------
    @property
    def secrets(self) -> SecretRepository:
        return self._get("secrets", SecretRepository)

    @property
    def secret_versions(self) -> SecretVersionRepository:
        return self._get("secret_versions", SecretVersionRepository)

    @property
    def secret_access_policies(self) -> SecretAccessPolicyRepository:
        return self._get("secret_access_policies", SecretAccessPolicyRepository)

    @property
    def secret_access_log(self) -> SecretAccessLogRepository:
        return self._get("secret_access_log", SecretAccessLogRepository)

    @property
    def encryption_keys(self) -> EncryptionKeyRepository:
        return self._get("encryption_keys", EncryptionKeyRepository)

    # -- risk -----------------------------------------------------------------------------
    @property
    def risk_scores(self) -> RiskScoreRepository:
        return self._get("risk_scores", RiskScoreRepository)

    # -- threats --------------------------------------------------------------------------
    @property
    def threat_detections(self) -> ThreatDetectionRepository:
        return self._get("threat_detections", ThreatDetectionRepository)

    # -- governance -----------------------------------------------------------------------
    @property
    def governance_assets(self) -> GovernanceAssetRepository:
        return self._get("governance_assets", GovernanceAssetRepository)

    @property
    def approval_policies(self) -> ApprovalPolicyRepository:
        return self._get("approval_policies", ApprovalPolicyRepository)

    @property
    def approval_requests(self) -> ApprovalRequestRepository:
        return self._get("approval_requests", ApprovalRequestRepository)

    @property
    def approval_decisions(self) -> ApprovalDecisionRepository:
        return self._get("approval_decisions", ApprovalDecisionRepository)

    # -- events / audit ---------------------------------------------------------------------
    @property
    def security_events(self) -> SecurityEventRepository:
        return self._get("security_events", SecurityEventRepository)

    @property
    def audit_log_entries(self) -> AuditLogEntryRepository:
        return self._get("audit_log_entries", AuditLogEntryRepository)

    # -- compliance -----------------------------------------------------------------------------
    @property
    def compliance_frameworks(self) -> ComplianceFrameworkConfigRepository:
        return self._get("compliance_frameworks", ComplianceFrameworkConfigRepository)

    @property
    def compliance_evidence(self) -> ComplianceEvidenceRepository:
        return self._get("compliance_evidence", ComplianceEvidenceRepository)

    @property
    def retention_policies(self) -> RetentionPolicyRepository:
        return self._get("retention_policies", RetentionPolicyRepository)

    @property
    def legal_holds(self) -> LegalHoldRepository:
        return self._get("legal_holds", LegalHoldRepository)

    @property
    def consent_records(self) -> ConsentRecordRepository:
        return self._get("consent_records", ConsentRecordRepository)

    @property
    def data_residency_records(self) -> DataResidencyRecordRepository:
        return self._get("data_residency_records", DataResidencyRecordRepository)
