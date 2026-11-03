"""Import every ORM model so `Base.metadata` is fully populated before
`init_models()`/Alembic autogenerate runs."""
from security_platform.models.compliance import (  # noqa: F401
    ComplianceEvidenceModel,
    ComplianceFrameworkConfigModel,
    ConsentRecordModel,
    DataResidencyRecordModel,
    LegalHoldModel,
    RetentionPolicyModel,
)
from security_platform.models.data_protection import (  # noqa: F401
    DataClassificationModel,
    DlpIncidentModel,
    DlpPolicyModel,
    PiiFindingModel,
)
from security_platform.models.events import AuditLogEntryModel, SecurityEventModel  # noqa: F401
from security_platform.models.governance import (  # noqa: F401
    ApprovalDecisionModel,
    ApprovalPolicyModel,
    ApprovalRequestModel,
    GovernanceAssetModel,
)
from security_platform.models.guardrails import (  # noqa: F401
    GuardrailEvaluationModel,
    GuardrailRuleModel,
    GuardrailViolationModel,
)
from security_platform.models.policies import PolicyExceptionModel, PolicyModel, PolicyVersionModel  # noqa: F401
from security_platform.models.risk import RiskScoreModel  # noqa: F401
from security_platform.models.secrets import (  # noqa: F401
    EncryptionKeyModel,
    SecretAccessLogModel,
    SecretAccessPolicyModel,
    SecretModel,
    SecretVersionModel,
)
from security_platform.models.threats import ThreatDetectionModel  # noqa: F401
