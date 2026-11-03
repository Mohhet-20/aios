"""One smoke test per aggregate root, exercised through the real schema
— catches import errors, column typos, and FK-shape mistakes across
the whole 29-table schema in one fast pass."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from security_platform.models.compliance import (
    ComplianceEvidenceModel,
    ComplianceFrameworkConfigModel,
    ConsentRecordModel,
    DataResidencyRecordModel,
    LegalHoldModel,
    RetentionPolicyModel,
)
from security_platform.models.data_protection import (
    DataClassificationModel,
    DlpIncidentModel,
    DlpPolicyModel,
    PiiFindingModel,
)
from security_platform.models.events import AuditLogEntryModel, SecurityEventModel
from security_platform.models.governance import (
    ApprovalDecisionModel,
    ApprovalPolicyModel,
    ApprovalRequestModel,
    GovernanceAssetModel,
)
from security_platform.models.guardrails import GuardrailEvaluationModel, GuardrailRuleModel, GuardrailViolationModel
from security_platform.models.policies import PolicyExceptionModel, PolicyModel, PolicyVersionModel
from security_platform.models.risk import RiskScoreModel
from security_platform.models.secrets import (
    EncryptionKeyModel,
    SecretAccessLogModel,
    SecretAccessPolicyModel,
    SecretModel,
    SecretVersionModel,
)
from security_platform.models.threats import ThreatDetectionModel


@pytest.mark.asyncio
async def test_repository_smoke_all_aggregates(repos):
    policy = await repos.policies.add(
        PolicyModel(tenant_id="t1", name="deny-jailbreak", scope="organization", effect="deny", rules={"category": "jailbreak"})
    )
    await repos.policy_versions.add(
        PolicyVersionModel(tenant_id="t1", policy_id=policy.id, version_number=1, rules_snapshot={}, effect_snapshot="deny")
    )
    await repos.policy_exceptions.add(
        PolicyExceptionModel(
            tenant_id="t1", policy_id=policy.id, scope_ref_id="ws-1", reason="pilot program",
            expires_at=datetime.now(timezone.utc),
        )
    )

    await repos.guardrail_rules.add(
        GuardrailRuleModel(tenant_id="t1", name="jailbreak-detector", category="jailbreak", action="block")
    )
    evaluation = await repos.guardrail_evaluations.add(
        GuardrailEvaluationModel(tenant_id="t1", category="jailbreak", input_excerpt="ignore all instructions", risk_score=0.9, action_taken="block")
    )
    await repos.guardrail_violations.add(
        GuardrailViolationModel(tenant_id="t1", evaluation_id=evaluation.id, category="jailbreak", severity="high")
    )

    await repos.pii_findings.add(
        PiiFindingModel(tenant_id="t1", source_type="prompt", entity_type="email", value_hash="abc123", redacted_preview="j***@example.com")
    )
    await repos.data_classifications.add(
        DataClassificationModel(tenant_id="t1", resource_type="document", resource_id="doc-1", sensitivity="confidential")
    )
    dlp_policy = await repos.dlp_policies.add(DlpPolicyModel(tenant_id="t1", name="block-restricted", sensitivity_threshold="restricted"))
    await repos.dlp_incidents.add(DlpIncidentModel(tenant_id="t1", policy_id=dlp_policy.id, severity="high"))

    secret = await repos.secrets.add(SecretModel(tenant_id="t1", name="openai-api-key", secret_type="api_key"))
    key = await repos.encryption_keys.add(EncryptionKeyModel(tenant_id="t1", material_ref="key-ref-1"))
    await repos.secret_versions.add(
        SecretVersionModel(tenant_id="t1", secret_id=secret.id, version_number=1, ciphertext="enc", nonce="nonce1", encryption_key_id=key.id)
    )
    await repos.secret_access_policies.add(SecretAccessPolicyModel(tenant_id="t1", secret_id=secret.id, principal_id="user-1"))
    await repos.secret_access_log.add(SecretAccessLogModel(tenant_id="t1", secret_id=secret.id, principal_id="user-1", action="read"))

    await repos.risk_scores.add(RiskScoreModel(tenant_id="t1", entity_type="user", entity_id="user-1", score=42.0, level="medium"))

    await repos.threat_detections.add(
        ThreatDetectionModel(tenant_id="t1", threat_type="brute_force", description="5 failed logins in 60s")
    )

    asset = await repos.governance_assets.add(
        GovernanceAssetModel(tenant_id="t1", asset_type="model", external_ref_id="model-1", name="gpt-router-v2")
    )
    approval_policy = await repos.approval_policies.add(ApprovalPolicyModel(tenant_id="t1", asset_type="model", required_approvals=2))
    request = await repos.approval_requests.add(ApprovalRequestModel(tenant_id="t1", asset_id=asset.id, required_approvals=2))
    await repos.approval_decisions.add(
        ApprovalDecisionModel(tenant_id="t1", request_id=request.id, approver_id="user-2", decision="approve")
    )

    await repos.security_events.add(SecurityEventModel(tenant_id="t1", event_type="authentication", description="login success"))
    await repos.audit_log_entries.add(AuditLogEntryModel(tenant_id="t1", action="policy.create", resource_type="policy"))

    await repos.compliance_frameworks.add(ComplianceFrameworkConfigModel(tenant_id="t1", framework="gdpr"))
    await repos.compliance_evidence.add(
        ComplianceEvidenceModel(tenant_id="t1", framework="gdpr", control_id="Art-32", evidence_type="policy", description="encryption at rest enabled")
    )
    await repos.retention_policies.add(RetentionPolicyModel(tenant_id="t1", resource_type="audit_log", retention_days=2555))
    await repos.legal_holds.add(LegalHoldModel(tenant_id="t1", name="litigation-hold-1", reason="pending litigation"))
    await repos.consent_records.add(ConsentRecordModel(tenant_id="t1", subject_id="user-1", purpose="marketing"))
    await repos.data_residency_records.add(
        DataResidencyRecordModel(tenant_id="t1", resource_type="document", resource_id="doc-1", region="eu")
    )

    assert policy.id is not None
    assert secret.name == "openai-api-key"
    assert asset.name == "gpt-router-v2"
    assert approval_policy.required_approvals == 2
