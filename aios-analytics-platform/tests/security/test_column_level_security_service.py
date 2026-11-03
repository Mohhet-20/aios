from __future__ import annotations

import pytest

from analytics_platform.core.exceptions import ValidationError
from analytics_platform.security.column_level_security_service import ColumnLevelSecurityService

TENANT = "cls-tenant"


@pytest.mark.asyncio
async def test_set_rule_rejects_bad_role(repos):
    service = ColumnLevelSecurityService(repos)
    with pytest.raises(ValidationError):
        await service.set_rule(TENANT, "kpis", restricted_columns=["target_value"], allowed_roles=["superuser"])


@pytest.mark.asyncio
async def test_redact_row_no_rule_passes_through(repos):
    service = ColumnLevelSecurityService(repos)
    row = {"name": "Revenue", "value": 1000}
    redacted = await service.redact_row(TENANT, "kpis", row, caller_role="viewer")
    assert redacted == row


@pytest.mark.asyncio
async def test_redact_row_strips_restricted_columns_for_low_role(repos):
    service = ColumnLevelSecurityService(repos)
    await service.set_rule(TENANT, "kpis", restricted_columns=["target_value", "cost_basis"], allowed_roles=["editor"])
    row = {"name": "Revenue", "value": 1000, "target_value": 5000, "cost_basis": 200}

    redacted = await service.redact_row(TENANT, "kpis", row, caller_role="viewer")
    assert "target_value" not in redacted
    assert "cost_basis" not in redacted
    assert redacted["name"] == "Revenue"


@pytest.mark.asyncio
async def test_redact_row_allows_sufficiently_high_role(repos):
    service = ColumnLevelSecurityService(repos)
    await service.set_rule(TENANT, "kpis", restricted_columns=["target_value"], allowed_roles=["editor"])
    row = {"name": "Revenue", "target_value": 5000}

    redacted_admin = await service.redact_row(TENANT, "kpis", row, caller_role="admin")
    assert redacted_admin == row

    redacted_analyst = await service.redact_row(TENANT, "kpis", row, caller_role="analyst")
    assert "target_value" not in redacted_analyst
