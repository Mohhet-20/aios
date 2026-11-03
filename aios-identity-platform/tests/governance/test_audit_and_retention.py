import pytest

from identity_platform.domain.enums import AuditActorType
from identity_platform.governance.audit_service import AuditService
from identity_platform.governance.retention_service import RetentionService

pytestmark = pytest.mark.asyncio


async def test_record_and_list_for_organization(repos, db_session):
    service = AuditService(repos)
    await service.record(
        actor_type=AuditActorType.USER, actor_id="user-1", action="role.assigned",
        resource_type="role_assignment", resource_id="assignment-1", organization_id="org-audit-1",
    )
    await service.record(
        actor_type=AuditActorType.USER, actor_id="user-1", action="organization.updated",
        resource_type="organization", resource_id="org-audit-1", organization_id="org-audit-1",
    )
    await db_session.commit()

    all_entries = await service.list_for_organization("org-audit-1")
    assert len(all_entries) == 2

    filtered = await service.list_for_organization("org-audit-1", action="role.assigned")
    assert len(filtered) == 1
    assert filtered[0].action == "role.assigned"


async def test_list_for_actor_and_resource(repos, db_session):
    service = AuditService(repos)
    await service.record(
        actor_type=AuditActorType.SERVICE_ACCOUNT, actor_id="svc-1", action="api_key.issued",
        resource_type="api_key", resource_id="key-1", after={"scopes": ["workflow:execute"]},
    )
    await db_session.commit()

    by_actor = await service.list_for_actor(AuditActorType.SERVICE_ACCOUNT, "svc-1")
    assert len(by_actor) == 1

    by_resource = await service.list_for_resource("api_key", "key-1")
    assert len(by_resource) == 1
    assert by_resource[0].after == {"scopes": ["workflow:execute"]}


async def test_retention_purges_old_entries(repos, db_session):
    from datetime import timedelta

    from identity_platform.config.settings import Settings
    from identity_platform.database.base import utcnow
    from identity_platform.models.governance import AuditLogEntryModel

    old_entry = AuditLogEntryModel(
        organization_id="org-retention", actor_type="user", actor_id="user-1", action="old.action",
        resource_type="organization", resource_id="org-retention", created_at=utcnow() - timedelta(days=1000),
    )
    recent_entry = AuditLogEntryModel(
        organization_id="org-retention", actor_type="user", actor_id="user-1", action="recent.action",
        resource_type="organization", resource_id="org-retention",
    )
    await repos.audit_log_entries.add(old_entry)
    await repos.audit_log_entries.add(recent_entry)
    await db_session.commit()

    settings = Settings(secret_key="x" * 32, audit_log_retention_days=730)
    retention_service = RetentionService(repos, settings=settings)
    purged = await retention_service.purge_expired_audit_logs()
    await db_session.commit()

    assert purged == 1
    remaining = await repos.audit_log_entries.list_for_organization("org-retention")
    assert len(remaining) == 1
    assert remaining[0].action == "recent.action"
