"""Deprecation notices: a message plus an optional planned removal
date, giving downstream consumers (SDK users, API integrators) an
explicit migration window instead of a surprise removal."""
from __future__ import annotations

from datetime import datetime, timezone

from docs_platform.models.versioning import DeprecationNoticeModel
from docs_platform.repositories.registry import RepositoryRegistry
from docs_platform.clock import utc_now


class DeprecationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_notice(
        self, tenant_id: str, *, subject_ref: str, message: str, removal_at: datetime | None = None
    ) -> DeprecationNoticeModel:
        notice = DeprecationNoticeModel(tenant_id=tenant_id, subject_ref=subject_ref, message=message, removal_at=removal_at)
        return await self.repos.deprecation_notices.add(notice)

    async def list_notices(self, tenant_id: str, *, limit: int = 100) -> list[DeprecationNoticeModel]:
        return await self.repos.deprecation_notices.list_for_tenant(tenant_id, limit=limit)

    def is_past_removal(self, notice: DeprecationNoticeModel, *, now: datetime | None = None) -> bool:
        if notice.removal_at is None:
            return False
        current = now or utc_now()
        removal_at = notice.removal_at
        if removal_at.tzinfo is None:
            removal_at = removal_at.replace(tzinfo=timezone.utc)
        return current >= removal_at
