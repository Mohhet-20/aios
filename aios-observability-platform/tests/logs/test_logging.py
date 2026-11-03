from __future__ import annotations

from datetime import timedelta

import pytest

from observability_platform.core.exceptions import LogPayloadTooLargeError, ValidationError
from observability_platform.database.base import utcnow
from observability_platform.logs.ingest_service import LogIngestService
from observability_platform.logs.retention_service import LogRetentionService
from observability_platform.logs.search_service import LogSearchService
from observability_platform.models.governance import RetentionPolicyModel
from observability_platform.models.logs import LogEntryModel


@pytest.mark.asyncio
async def test_ingest_masks_sensitive_context(repos):
    svc = LogIngestService(repos)
    entry = await svc.ingest(
        "t1", service_name="auth", level="info", message="login attempt",
        context={"password": "hunter2", "user": "mo"}, correlation_id="corr-1",
    )
    assert entry.context["password"] == "***REDACTED***"
    assert entry.context["user"] == "mo"


@pytest.mark.asyncio
async def test_ingest_rejects_unknown_level(repos):
    svc = LogIngestService(repos)
    with pytest.raises(ValidationError):
        await svc.ingest("t1", service_name="auth", level="not-a-level", message="x")


@pytest.mark.asyncio
async def test_ingest_rejects_oversized_message(repos):
    svc = LogIngestService(repos)
    svc.settings.log_max_message_bytes = 10
    with pytest.raises(LogPayloadTooLargeError):
        await svc.ingest("t1", service_name="auth", level="info", message="x" * 100)


@pytest.mark.asyncio
async def test_search_filters_by_level_and_service(repos):
    ingest = LogIngestService(repos)
    await ingest.ingest("t1", service_name="api", level="error", message="boom")
    await ingest.ingest("t1", service_name="api", level="info", message="ok")
    await ingest.ingest("t1", service_name="worker", level="error", message="boom2")

    search = LogSearchService(repos)
    errors = await search.search("t1", level="error")
    assert len(errors) == 2
    api_errors = await search.search("t1", level="error", service_name="api")
    assert len(api_errors) == 1
    assert api_errors[0].message == "boom"


@pytest.mark.asyncio
async def test_search_by_correlation_id_stitches_cross_service_logs(repos):
    ingest = LogIngestService(repos)
    await ingest.ingest("t1", service_name="api", level="info", message="start", correlation_id="req-42")
    await ingest.ingest("t1", service_name="worker", level="info", message="processed", correlation_id="req-42")
    await ingest.ingest("t1", service_name="worker", level="info", message="unrelated", correlation_id="req-99")

    search = LogSearchService(repos)
    stitched = await search.by_correlation_id("t1", "req-42")
    assert len(stitched) == 2
    assert {e.service_name for e in stitched} == {"api", "worker"}


@pytest.mark.asyncio
async def test_level_counts(repos):
    ingest = LogIngestService(repos)
    await ingest.ingest("t1", service_name="api", level="error", message="a")
    await ingest.ingest("t1", service_name="api", level="error", message="b")
    await ingest.ingest("t1", service_name="api", level="info", message="c")

    search = LogSearchService(repos)
    counts = await search.level_counts("t1")
    assert counts["error"] == 2
    assert counts["info"] == 1


@pytest.mark.asyncio
async def test_retention_sweep_deletes_only_expired_and_respects_tenant(repos):
    old = LogEntryModel(
        tenant_id="t1", service_name="api", level="info", message="old", context={}, tags={},
        event_time=utcnow() - timedelta(days=100),
    )
    recent = LogEntryModel(
        tenant_id="t1", service_name="api", level="info", message="recent", context={}, tags={},
        event_time=utcnow(),
    )
    other_tenant_old = LogEntryModel(
        tenant_id="t2", service_name="api", level="info", message="old-other-tenant", context={}, tags={},
        event_time=utcnow() - timedelta(days=100),
    )
    await repos.log_entries.add(old)
    await repos.log_entries.add(recent)
    await repos.log_entries.add(other_tenant_old)

    retention = LogRetentionService(repos)
    deleted = await retention.sweep_expired("t1")
    assert deleted == 1

    remaining_t1 = await repos.log_entries.search("t1", limit=10)
    assert len(remaining_t1) == 1
    assert remaining_t1[0].message == "recent"

    remaining_t2 = await repos.log_entries.search("t2", limit=10)
    assert len(remaining_t2) == 1  # untouched by t1's sweep


@pytest.mark.asyncio
async def test_retention_respects_per_tenant_policy_override(repos):
    old_but_within_custom_window = LogEntryModel(
        tenant_id="t1", service_name="api", level="info", message="keep-me", context={}, tags={},
        event_time=utcnow() - timedelta(days=45),
    )
    await repos.log_entries.add(old_but_within_custom_window)
    await repos.retention_policies.add(
        RetentionPolicyModel(tenant_id="t1", resource_type="logs", retention_days=60, is_enabled=True)
    )

    retention = LogRetentionService(repos)
    deleted = await retention.sweep_expired("t1")
    assert deleted == 0  # 45 days old, within the 60-day custom policy
