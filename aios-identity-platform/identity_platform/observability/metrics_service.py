"""ObservabilityMetricsService: computes identity-platform metrics on
demand via direct aggregate queries rather than maintaining a
separately-written metrics/events table — the same "count don't cache"
philosophy `TenantUsageService` uses (Task 142), extended to every
signal the design calls for: auth success/failure rates, session
activity, permission (role-assignment) usage, API key usage, org
growth, workspace activity, and security events. These queries run
directly against the shared `AsyncSession` (`repos.session`) rather
than through per-resource repositories, since they're cross-cutting
analytical aggregates, not single-resource CRUD."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select

from identity_platform.database.base import utcnow
from identity_platform.models.api_key import ApiKeyModel
from identity_platform.models.organization import OrganizationModel
from identity_platform.models.rbac import RoleAssignmentModel, RoleModel
from identity_platform.models.security import SecurityEventModel
from identity_platform.models.session import LoginHistoryModel, SessionModel
from identity_platform.models.workspace import WorkspaceModel
from identity_platform.repositories.registry import RepositoryRegistry


class ObservabilityMetricsService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def auth_metrics(self, *, since: datetime | None = None) -> dict:
        stmt = select(LoginHistoryModel.success, func.count()).group_by(LoginHistoryModel.success)
        if since is not None:
            stmt = stmt.where(LoginHistoryModel.created_at >= since)
        rows = (await self.repos.session.execute(stmt)).all()
        counts = {bool(success): count for success, count in rows}
        successes = counts.get(True, 0)
        failures = counts.get(False, 0)
        total = successes + failures
        return {
            "total_attempts": total, "successes": successes, "failures": failures,
            "success_rate": round(successes / total, 4) if total else None,
        }

    async def session_metrics(self) -> dict:
        stmt = select(SessionModel.status, func.count()).group_by(SessionModel.status)
        rows = (await self.repos.session.execute(stmt)).all()
        by_status = {status: count for status, count in rows}
        return {
            "active_sessions": by_status.get("active", 0), "revoked_sessions": by_status.get("revoked", 0),
            "expired_sessions": by_status.get("expired", 0),
        }

    async def api_key_usage(self, organization_id: str) -> dict:
        total_stmt = select(func.count()).where(ApiKeyModel.organization_id == organization_id)
        active_stmt = total_stmt.where(ApiKeyModel.status == "active")
        recently_used_stmt = active_stmt.where(ApiKeyModel.last_used_at >= utcnow() - timedelta(days=30))

        total = (await self.repos.session.execute(total_stmt)).scalar_one()
        active = (await self.repos.session.execute(active_stmt)).scalar_one()
        recently_used = (await self.repos.session.execute(recently_used_stmt)).scalar_one()
        return {"total_keys": total, "active_keys": active, "used_last_30_days": recently_used}

    async def organization_growth(self, *, since: datetime) -> dict:
        stmt = select(func.count()).where(OrganizationModel.created_at >= since, OrganizationModel.is_deleted.is_(False))
        new_orgs = (await self.repos.session.execute(stmt)).scalar_one()
        total_stmt = select(func.count()).where(OrganizationModel.is_deleted.is_(False))
        total_orgs = (await self.repos.session.execute(total_stmt)).scalar_one()
        return {"new_organizations": new_orgs, "total_organizations": total_orgs, "since": since.isoformat()}

    async def workspace_activity(self, organization_id: str) -> dict:
        stmt = select(WorkspaceModel.status, func.count()).where(
            WorkspaceModel.organization_id == organization_id
        ).group_by(WorkspaceModel.status)
        rows = (await self.repos.session.execute(stmt)).all()
        by_status = {status: count for status, count in rows}
        return {"active_workspaces": by_status.get("active", 0), "archived_workspaces": by_status.get("archived", 0)}

    async def permission_usage(self, organization_id: str) -> list[dict]:
        stmt = (
            select(RoleModel.slug, RoleModel.name, func.count(RoleAssignmentModel.id))
            .join(RoleAssignmentModel, RoleAssignmentModel.role_id == RoleModel.id)
            .where(RoleAssignmentModel.scope_id == organization_id, RoleAssignmentModel.revoked_at.is_(None))
            .group_by(RoleModel.slug, RoleModel.name)
        )
        rows = (await self.repos.session.execute(stmt)).all()
        return [{"role_slug": slug, "role_name": name, "active_assignments": count} for slug, name, count in rows]

    async def security_overview(self, organization_id: str) -> dict:
        stmt = select(SecurityEventModel.severity, func.count()).where(
            SecurityEventModel.organization_id == organization_id
        ).group_by(SecurityEventModel.severity)
        rows = (await self.repos.session.execute(stmt)).all()
        by_severity = {severity: count for severity, count in rows}
        unresolved = await self.repos.security_events.list_unresolved(organization_id)
        return {
            "events_by_severity": by_severity, "unresolved_count": len(unresolved),
            "total_events": sum(by_severity.values()),
        }
