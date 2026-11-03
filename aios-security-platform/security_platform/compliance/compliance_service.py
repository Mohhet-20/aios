"""Compliance: framework configuration (GDPR/SOC2/ISO27001/HIPAA-ready
design/custom), evidence collection against specific controls,
retention policy configuration, legal holds (which take precedence
over retention deletion — a resource under an active hold cannot be
deleted even if its retention window has elapsed), consent tracking,
and data residency enforcement."""
from __future__ import annotations

from security_platform.config.settings import Settings, get_settings
from security_platform.core.exceptions import (
    ConsentRequiredError,
    DataResidencyViolationError,
    LegalHoldActiveError,
    ValidationError,
)
from security_platform.database.base import utcnow
from security_platform.domain.entities import _aware
from security_platform.domain.enums import ConsentStatus, LegalHoldStatus
from security_platform.models.compliance import (
    ComplianceEvidenceModel,
    ComplianceFrameworkConfigModel,
    ConsentRecordModel,
    DataResidencyRecordModel,
    LegalHoldModel,
    RetentionPolicyModel,
)
from security_platform.repositories.registry import RepositoryRegistry


class ComplianceService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    # -- frameworks -----------------------------------------------------------------

    async def enable_framework(self, tenant_id: str, framework: str, *, notes: str | None = None) -> ComplianceFrameworkConfigModel:
        existing = await self.repos.compliance_frameworks.get_for_framework(tenant_id, framework)
        if existing is not None:
            existing.is_enabled = True
            if notes is not None:
                existing.notes = notes
            return await self.repos.compliance_frameworks.update(existing)
        return await self.repos.compliance_frameworks.add(
            ComplianceFrameworkConfigModel(tenant_id=tenant_id, framework=framework, is_enabled=True, notes=notes)
        )

    async def disable_framework(self, tenant_id: str, framework: str) -> ComplianceFrameworkConfigModel:
        existing = await self.repos.compliance_frameworks.get_for_framework(tenant_id, framework)
        if existing is None:
            raise ValidationError(f"Compliance framework '{framework}' is not configured for this tenant")
        existing.is_enabled = False
        return await self.repos.compliance_frameworks.update(existing)

    async def list_enabled_frameworks(self, tenant_id: str) -> list[ComplianceFrameworkConfigModel]:
        return await self.repos.compliance_frameworks.list_enabled(tenant_id)

    # -- evidence ---------------------------------------------------------------------

    async def collect_evidence(
        self, tenant_id: str, framework: str, control_id: str, evidence_type: str, description: str, *, resource_ref: str | None = None
    ) -> ComplianceEvidenceModel:
        return await self.repos.compliance_evidence.add(
            ComplianceEvidenceModel(
                tenant_id=tenant_id, framework=framework, control_id=control_id, evidence_type=evidence_type,
                description=description, resource_ref=resource_ref,
            )
        )

    async def evidence_for_framework(self, tenant_id: str, framework: str, *, limit: int = 500) -> list[ComplianceEvidenceModel]:
        return await self.repos.compliance_evidence.list_for_framework(tenant_id, framework, limit=limit)

    # -- retention & legal hold -------------------------------------------------------

    async def set_retention_policy(self, tenant_id: str, resource_type: str, retention_days: int, *, is_enabled: bool = True) -> RetentionPolicyModel:
        existing = await self.repos.retention_policies.get_for_resource(tenant_id, resource_type)
        if existing is not None:
            existing.retention_days = retention_days
            existing.is_enabled = is_enabled
            return await self.repos.retention_policies.update(existing)
        return await self.repos.retention_policies.add(
            RetentionPolicyModel(tenant_id=tenant_id, resource_type=resource_type, retention_days=retention_days, is_enabled=is_enabled)
        )

    async def open_legal_hold(self, tenant_id: str, name: str, reason: str, *, resource_type: str | None = None, resource_id: str | None = None) -> LegalHoldModel:
        return await self.repos.legal_holds.add(
            LegalHoldModel(
                tenant_id=tenant_id, name=name, reason=reason, resource_type=resource_type, resource_id=resource_id,
                status=LegalHoldStatus.ACTIVE.value,
            )
        )

    async def release_legal_hold(self, tenant_id: str, hold_id: str) -> LegalHoldModel:
        hold = await self.repos.legal_holds.get_or_404(hold_id)
        if hold.status != LegalHoldStatus.ACTIVE.value:
            raise ValidationError(f"Legal hold '{hold_id}' is not active")
        hold.status = LegalHoldStatus.RELEASED.value
        hold.released_at = utcnow()
        return await self.repos.legal_holds.update(hold)

    async def check_deletion_allowed(self, tenant_id: str, resource_type: str, resource_id: str) -> bool:
        """Raises LegalHoldActiveError if an active legal hold covers
        this resource and `legal_hold_overrides_retention` is set
        (the default posture); otherwise returns True."""
        holds = await self.repos.legal_holds.list_active_for_resource(tenant_id, resource_type, resource_id)
        if holds and self.settings.legal_hold_overrides_retention:
            raise LegalHoldActiveError(
                f"Cannot delete {resource_type} '{resource_id}': under active legal hold(s) {[h.id for h in holds]}"
            )
        return True

    # -- consent ------------------------------------------------------------------------

    async def record_consent(self, tenant_id: str, subject_id: str, purpose: str, *, expires_at=None) -> ConsentRecordModel:
        return await self.repos.consent_records.add(
            ConsentRecordModel(
                tenant_id=tenant_id, subject_id=subject_id, purpose=purpose, status=ConsentStatus.GRANTED.value,
                granted_at=utcnow(), expires_at=expires_at,
            )
        )

    async def withdraw_consent(self, tenant_id: str, subject_id: str, purpose: str) -> ConsentRecordModel:
        active = await self.repos.consent_records.get_active_for_subject(tenant_id, subject_id, purpose)
        if active is None:
            raise ValidationError(f"No active consent found for subject '{subject_id}' / purpose '{purpose}'")
        active.status = ConsentStatus.WITHDRAWN.value
        active.withdrawn_at = utcnow()
        return await self.repos.consent_records.update(active)

    async def require_consent(self, tenant_id: str, subject_id: str, purpose: str) -> ConsentRecordModel:
        active = await self.repos.consent_records.get_active_for_subject(tenant_id, subject_id, purpose)
        if active is None:
            raise ConsentRequiredError(f"No active consent for subject '{subject_id}' / purpose '{purpose}'")
        if active.expires_at is not None and _aware(active.expires_at) <= utcnow():
            raise ConsentRequiredError(f"Consent for subject '{subject_id}' / purpose '{purpose}' has expired")
        return active

    async def is_consent_active(self, tenant_id: str, subject_id: str, purpose: str) -> bool:
        try:
            await self.require_consent(tenant_id, subject_id, purpose)
            return True
        except ConsentRequiredError:
            return False

    # -- data residency -------------------------------------------------------------------

    async def record_residency(self, tenant_id: str, resource_type: str, resource_id: str, region: str) -> DataResidencyRecordModel:
        existing = await self.repos.data_residency_records.get_for_resource(tenant_id, resource_type, resource_id)
        if existing is not None:
            existing.region = region
            return await self.repos.data_residency_records.update(existing)
        return await self.repos.data_residency_records.add(
            DataResidencyRecordModel(tenant_id=tenant_id, resource_type=resource_type, resource_id=resource_id, region=region)
        )

    async def check_residency_allowed(self, tenant_id: str, resource_type: str, resource_id: str, allowed_regions: list[str]) -> bool:
        record = await self.repos.data_residency_records.get_for_resource(tenant_id, resource_type, resource_id)
        region = record.region if record is not None else self.settings.default_data_residency_region
        if region not in allowed_regions:
            raise DataResidencyViolationError(
                f"{resource_type} '{resource_id}' resides in region '{region}', which is outside the allowed regions {allowed_regions}"
            )
        return True
