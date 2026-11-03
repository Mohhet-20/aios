"""Tests for PII detection/redaction and sensitive data classification."""
from __future__ import annotations

import pytest

from security_platform.config.settings import Settings
from security_platform.domain.enums import DataSensitivity, PiiEntityType
from security_platform.pii.detectors import detect_pii, mask_value, redact_pii
from security_platform.pii.pii_service import PiiService

TENANT = "tenant-pii"
VALID_VISA = "4111111111111111"  # passes Luhn


def test_detect_pii_finds_email_and_phone():
    matches = detect_pii("Reach me at ada@example.com or 555-123-4567.")
    entity_types = {m.entity_type for m in matches}
    assert PiiEntityType.EMAIL in entity_types
    assert PiiEntityType.PHONE in entity_types


def test_detect_pii_finds_ssn():
    matches = detect_pii("SSN on file: 123-45-6789.")
    assert any(m.entity_type == PiiEntityType.SSN for m in matches)


def test_detect_pii_credit_card_requires_luhn_checksum():
    valid = detect_pii(f"Card: {VALID_VISA}")
    assert any(m.entity_type == PiiEntityType.CREDIT_CARD for m in valid)
    invalid = detect_pii("Card: 1234567890123456")
    assert not any(m.entity_type == PiiEntityType.CREDIT_CARD for m in invalid)


def test_detect_pii_no_false_positive_on_clean_text():
    assert detect_pii("The quarterly report is due Friday.") == []


def test_redact_pii_replaces_matches_with_placeholders():
    text = "Email ada@example.com now."
    redacted = redact_pii(text)
    assert "ada@example.com" not in redacted
    assert "[EMAIL]" in redacted


def test_mask_value_keeps_last_four_digits_for_card():
    masked = mask_value(VALID_VISA, PiiEntityType.CREDIT_CARD)
    assert masked == "***1111"


def test_mask_value_partially_masks_email():
    masked = mask_value("ada@example.com", PiiEntityType.EMAIL)
    assert masked.endswith("@example.com")
    assert "ada" not in masked


@pytest.mark.asyncio
async def test_scan_pii_persists_findings_without_raw_value(repos):
    service = PiiService(repos, settings=Settings())
    findings = await service.scan_pii(TENANT, "chat_message", "msg-1", "Contact ada@example.com please.")
    assert len(findings) == 1
    assert findings[0].entity_type == PiiEntityType.EMAIL.value
    assert "ada@example.com" not in findings[0].redacted_preview
    assert len(findings[0].value_hash) == 64  # sha256 hex digest


@pytest.mark.asyncio
async def test_classify_resource_creates_then_updates_in_place(repos):
    service = PiiService(repos, settings=Settings())
    first = await service.classify_resource(TENANT, "document", "doc-1", DataSensitivity.INTERNAL.value)
    assert first.sensitivity == DataSensitivity.INTERNAL.value

    second = await service.classify_resource(TENANT, "document", "doc-1", DataSensitivity.RESTRICTED.value, rationale="Contains SSNs")
    assert second.id == first.id
    assert second.sensitivity == DataSensitivity.RESTRICTED.value
    assert second.rationale == "Contains SSNs"
