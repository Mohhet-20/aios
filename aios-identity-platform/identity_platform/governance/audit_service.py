"""AuditService: the single write path for `AuditLogEntryModel` — every
governance-relevant mutation across this platform (role changes, org
settings edits, invitation acceptance, API key issuance, security
recovery actions) should route through `record` rather than writing
the model directly, so `action`/`resource_type` naming stays
consistent for anyone later querying "who did what, when." `before`/
`after` are optional snapshots for changes where a diff is meaningful
(e.g. a settings update); purely additive actions (e.g. "api_key
issued") only need `after`."""
from __future__ import annotations

from identity_platform.domain.enums import AuditActorType
from identity_platform.models.governance import AuditLogEntryModel
from identity_platform.repositories.registry import RepositoryRegistry


class AuditService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record(
        self, *, actor_type: AuditActorType, actor_id: str, action: str, resource_type: str, resource_id: str,
        organization_id: str | None = None, before: dict | None = None, after: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLogEntryModel:
        return await self.repos.audit_log_entries.add(AuditLogEntryModel(
            organization_id=organization_id, actor_type=actor_type.value, actor_id=actor_id, action=action,
            resource_type=resource_type, resource_id=resource_id, before=before, after=after, ip_address=ip_address,
        ))

    async def list_for_organization(self, organization_id: str, *, action: str | None = None, limit: int = 100) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log_entries.list_for_organization(organization_id, action=action, limit=limit)

    async def list_for_actor(self, actor_type: AuditActorType, actor_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log_entries.list_for_actor(actor_type.value, actor_id, limit=limit)

    async def list_for_resource(self, resource_type: str, resource_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log_entries.list_for_resource(resource_type, resource_id, limit=limit)
