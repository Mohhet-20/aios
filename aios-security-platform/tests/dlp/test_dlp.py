"""Tests for DLP policy evaluation (allow/flag/redact/block) and
secure context assembly."""
from __future__ import annotations

import pytest

from security_platform.config.settings import Settings
from security_platform.core.exceptions import DlpBlockError
from security_platform.dlp.dlp_service import DlpService
from security_platform.domain.enums import DataSensitivity, DlpAction
from security_platform.models.data_protection import DlpPolicyModel
from security_platform.pii.pii_service import PiiService

TENANT = "tenant-dlp"


@pytest.mark.asyncio
async def test_evaluate_dlp_allows_clean_text(repos):
    service = DlpService(repos, settings=Settings())
    incidents, action, output = await service.evaluate_dlp(TENANT, "Nothing sensitive here.")
    assert incidents == []
    assert action == DlpAction.ALLOW.value


@pytest.mark.asyncio
async def test_evaluate_dlp_allows_when_no_policy_configured(repos):
    service = DlpService(repos, settings=Settings())
    incidents, action, output = await service.evaluate_dlp(TENANT, "Email me at ada@example.com")
    assert incidents == []
    assert action == DlpAction.ALLOW.value  # no enabled policy -> nothing triggers


@pytest.mark.asyncio
async def test_evaluate_dlp_redacts_when_policy_action_is_redact(repos):
    await repos.dlp_policies.add(
        DlpPolicyModel(tenant_id=TENANT, name="internal-pii", sensitivity_threshold=DataSensitivity.INTERNAL.value, action=DlpAction.REDACT.value)
    )
    service = DlpService(repos, settings=Settings())
    incidents, action, output = await service.evaluate_dlp(TENANT, "Email me at ada@example.com")
    assert action == DlpAction.REDACT.value
    assert len(incidents) == 1
    assert "ada@example.com" not in output
    assert "[EMAIL]" in output


@pytest.mark.asyncio
async def test_evaluate_dlp_blocks_on_critical_restricted_pii(repos):
    await repos.dlp_policies.add(
        DlpPolicyModel(tenant_id=TENANT, name="restricted-flag", sensitivity_threshold=DataSensitivity.RESTRICTED.value, action=DlpAction.FLAG.value)
    )
    service = DlpService(repos, settings=Settings(dlp_block_on_critical=True))
    with pytest.raises(DlpBlockError):
        await service.evaluate_dlp(TENANT, "SSN: 123-45-6789")
    incidents = await repos.dlp_incidents.list_recent(TENANT)
    assert len(incidents) == 1
    assert incidents[0].action_taken == DlpAction.BLOCK.value
    assert incidents[0].severity == "critical"


@pytest.mark.asyncio
async def test_assemble_secure_context_drops_over_sensitive_fragments_and_redacts_rest(repos):
    pii_service = PiiService(repos, settings=Settings())
    dlp_service = DlpService(repos, settings=Settings())
    await pii_service.classify_resource(TENANT, "document", "doc-secret", DataSensitivity.RESTRICTED.value)
    await pii_service.classify_resource(TENANT, "document", "doc-public", DataSensitivity.INTERNAL.value)

    fragments = [
        {"text": "Top secret contents.", "resource_type": "document", "resource_id": "doc-secret"},
        {"text": "Public info, contact ada@example.com.", "resource_type": "document", "resource_id": "doc-public"},
        {"text": "No classification attached.", "resource_type": None, "resource_id": None},
    ]
    safe = await dlp_service.assemble_secure_context(TENANT, fragments, max_sensitivity=DataSensitivity.CONFIDENTIAL.value)
    assert len(safe) == 2
    assert not any("Top secret" in s for s in safe)
    assert any("[EMAIL]" in s for s in safe)
