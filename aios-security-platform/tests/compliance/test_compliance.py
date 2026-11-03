"""Tests for the Compliance module: framework configuration, evidence
collection, retention policy upserts, legal holds overriding deletion,
consent tracking (grant/withdraw/require/expiry), and data residency
enforcement."""
from __future__ import annotations

from datetime import timedelta

import pytest

from security_platform.compliance.compliance_service import ComplianceService
from security_platform.config.settings import Settings
from security_platform.core.exceptions import ConsentRequiredError, DataResidencyViolationError, LegalHoldActiveError, ValidationError
from security_platform.database.base import utcnow
from security_platform.domain.enums import ComplianceFramework

TENANT = "tenant-compliance"


@pytest.mark.asyncio
async def test_enable_framework_is_idempotent_and_disable_works(repos):
    service = ComplianceService(repos)
    first = await service.enable_framework(TENANT, ComplianceFramework.GDPR.value, notes="Initial setup")
    second = await service.enable_framework(TENANT, ComplianceFramework.GDPR.value, notes="Updated notes")
    assert first.id == second.id
    assert second.notes == "Updated notes"

    disabled = await service.disable_framework(TENANT, ComplianceFramework.GDPR.value)
    assert disabled.is_enabled is False
    enabled_list = await service.list_enabled_frameworks(TENANT)
    assert all(f.framework != ComplianceFramework.GDPR.value for f in enabled_list)


@pytest.mark.asyncio
async def test_disable_unknown_framework_raises(repos):
    service = ComplianceService(repos)
    with pytest.raises(ValidationError):
        await service.disable_framework(TENANT, ComplianceFramework.HIPAA.value)


@pytest.mark.asyncio
async def test_collect_and_list_evidence(repos):
    service = ComplianceService(repos)
    await service.collect_evidence(TENANT, ComplianceFramework.SOC2.value, "CC6.1", "access_review", "Quarterly access review completed")
    await service.collect_evidence(TENANT, ComplianceFramework.SOC2.value, "CC6.1", "access_review", "Follow-up review completed")
    evidence = await service.evidence_for_framework(TENANT, ComplianceFramework.SOC2.value)
    assert len(evidence) == 2


@pytest.mark.asyncio
async def test_set_retention_policy_upserts(repos):
    service = ComplianceService(repos)
    first = await service.set_retention_policy(TENANT, "chat_message", 90)
    assert first.retention_days == 90
    second = await service.set_retention_policy(TENANT, "chat_message", 180)
    assert second.id == first.id
    assert second.retention_days == 180


@pytest.mark.asyncio
async def test_legal_hold_blocks_deletion_until_released(repos):
    service = ComplianceService(repos, settings=Settings(legal_hold_overrides_retention=True))
    hold = await service.open_legal_hold(TENANT, "Litigation Hold #1", "Pending litigation", resource_type="document", resource_id="doc-1")

    with pytest.raises(LegalHoldActiveError):
        await service.check_deletion_allowed(TENANT, "document", "doc-1")

    released = await service.release_legal_hold(TENANT, hold.id)
    assert released.status == "released"
    assert released.released_at is not None

    assert await service.check_deletion_allowed(TENANT, "document", "doc-1") is True


@pytest.mark.asyncio
async def test_release_already_released_hold_raises(repos):
    service = ComplianceService(repos)
    hold = await service.open_legal_hold(TENANT, "Hold #2", "Investigation", resource_type="document", resource_id="doc-2")
    await service.release_legal_hold(TENANT, hold.id)
    with pytest.raises(ValidationError):
        await service.release_legal_hold(TENANT, hold.id)


@pytest.mark.asyncio
async def test_deletion_allowed_when_no_active_hold(repos):
    service = ComplianceService(repos)
    assert await service.check_deletion_allowed(TENANT, "document", "doc-no-hold") is True


@pytest.mark.asyncio
async def test_consent_grant_require_withdraw(repos):
    service = ComplianceService(repos)
    with pytest.raises(ConsentRequiredError):
        await service.require_consent(TENANT, "subject-1", "marketing_emails")

    await service.record_consent(TENANT, "subject-1", "marketing_emails")
    assert await service.is_consent_active(TENANT, "subject-1", "marketing_emails") is True

    withdrawn = await service.withdraw_consent(TENANT, "subject-1", "marketing_emails")
    assert withdrawn.status == "withdrawn"
    assert await service.is_consent_active(TENANT, "subject-1", "marketing_emails") is False


@pytest.mark.asyncio
async def test_consent_expiry_makes_require_consent_raise(repos):
    service = ComplianceService(repos)
    await service.record_consent(TENANT, "subject-2", "analytics", expires_at=utcnow() - timedelta(days=1))
    with pytest.raises(ConsentRequiredError):
        await service.require_consent(TENANT, "subject-2", "analytics")


@pytest.mark.asyncio
async def test_withdraw_consent_without_active_grant_raises(repos):
    service = ComplianceService(repos)
    with pytest.raises(ValidationError):
        await service.withdraw_consent(TENANT, "subject-3", "unused_purpose")


@pytest.mark.asyncio
async def test_data_residency_check_uses_recorded_region_or_default(repos):
    service = ComplianceService(repos, settings=Settings(default_data_residency_region="us"))
    assert await service.check_residency_allowed(TENANT, "document", "doc-unrecorded", ["us", "eu"]) is True

    await service.record_residency(TENANT, "document", "doc-eu", "eu")
    assert await service.check_residency_allowed(TENANT, "document", "doc-eu", ["us", "eu"]) is True
    with pytest.raises(DataResidencyViolationError):
        await service.check_residency_allowed(TENANT, "document", "doc-eu", ["us"])


@pytest.mark.asyncio
async def test_record_residency_updates_in_place(repos):
    service = ComplianceService(repos)
    first = await service.record_residency(TENANT, "document", "doc-move", "us")
    second = await service.record_residency(TENANT, "document", "doc-move", "eu")
    assert first.id == second.id
    assert second.region == "eu"
