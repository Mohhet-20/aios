from datetime import datetime, timedelta, timezone

import pytest

from eval_platform.config import settings as settings_module
from eval_platform.models.observability import ObservabilityEventModel


@pytest.mark.asyncio
async def test_sweep_removes_only_stale_events(retention_service, workspace, repos, monkeypatch):
    settings_module.get_settings.cache_clear()
    monkeypatch.setenv("OBSERVABILITY_EVENT_RETENTION_DAYS", "30")
    settings_module.get_settings.cache_clear()
    try:
        fresh = await repos.observability_events.add(ObservabilityEventModel(
            workspace_id=workspace.id, event_type="tool_call", source_platform="tool_platform", status="succeeded",
        ))
        stale = await repos.observability_events.add(ObservabilityEventModel(
            workspace_id=workspace.id, event_type="tool_call", source_platform="tool_platform", status="succeeded",
        ))
        stale.created_at = datetime.now(timezone.utc) - timedelta(days=60)
        await repos.observability_events.update(stale)

        removed = await retention_service.sweep_observability_events()
        assert removed == 1

        remaining = await repos.observability_events.get(fresh.id)
        assert remaining is not None
        gone = await repos.observability_events.get(stale.id)
        assert gone is None
    finally:
        settings_module.get_settings.cache_clear()
