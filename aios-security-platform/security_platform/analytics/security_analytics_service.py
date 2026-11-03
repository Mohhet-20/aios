"""Security Observability & Analytics: read-only aggregation views
over every other module in this platform — threat trends, guardrail
("policy") violations, risk score distribution, combined security
incident counts, compliance posture, secrets usage, encryption key
status, and governance metrics. Nothing here writes state; it exists
purely to answer dashboard-shaped questions cheaply by delegating to
the `count_by_*`/`list_*` aggregate queries already exposed on each
module's repository.

Note on naming: the platform has no standalone "policy violation" log
table — `PolicyEvaluationService.evaluate()` returns an allow/deny
decision without persisting a row for every check (that would be an
extremely high-volume table for a synchronous check). What *is*
persisted is `GuardrailViolationModel`, which includes a
`policy_violation` category alongside the AI-guardrail categories, so
`policy_violation_summary` reports from that log. This is a disclosed
scope choice, not an oversight."""
from __future__ import annotations

from datetime import timedelta

from security_platform.config.settings import Settings, get_settings
from security_platform.domain.entities import _now
from security_platform.domain.enums import RiskLevel
from security_platform.repositories.registry import RepositoryRegistry


class SecurityAnalyticsService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def threat_trends(self, tenant_id: str, *, since_hours: int = 24) -> dict[str, int]:
        start_time = _now() - timedelta(hours=since_hours)
        return await self.repos.threat_detections.count_by_type(tenant_id, start_time=start_time)

    async def policy_violation_summary(self, tenant_id: str) -> dict[str, int]:
        return await self.repos.guardrail_violations.count_by_category(tenant_id)

    async def risk_score_distribution(self, tenant_id: str, entity_type: str, *, limit: int = 500) -> dict[str, int]:
        scores = await self.repos.risk_scores.list_highest_current(tenant_id, entity_type, limit=limit)
        distribution = {level.value: 0 for level in RiskLevel}
        for score in scores:
            distribution[score.level] = distribution.get(score.level, 0) + 1
        return distribution

    async def security_incident_summary(self, tenant_id: str) -> dict[str, dict[str, int]]:
        return {
            "threats_by_status": await self.repos.threat_detections.count_by_status(tenant_id),
            "guardrail_violations_by_status": await self.repos.guardrail_violations.count_by_category(tenant_id),
        }

    async def compliance_status(self, tenant_id: str) -> dict:
        enabled = await self.repos.compliance_frameworks.list_enabled(tenant_id)
        active_holds = await self.repos.legal_holds.list_active(tenant_id)
        return {
            "enabled_frameworks": [f.framework for f in enabled],
            "active_legal_holds": len(active_holds),
        }

    async def secrets_usage_summary(self, tenant_id: str, *, since_hours: int = 24) -> dict:
        start_time = _now() - timedelta(hours=since_hours)
        return {
            "by_status": await self.repos.secrets.count_by_status(tenant_id),
            "recent_access_attempts": await self.repos.secret_access_log.count_since(tenant_id, start_time=start_time),
            "recent_access_failures": await self.repos.secret_access_log.count_since(tenant_id, start_time=start_time, success=False),
        }

    async def encryption_status(self, tenant_id: str) -> dict[str, int]:
        return await self.repos.encryption_keys.count_by_status(tenant_id)

    async def governance_metrics(self, tenant_id: str) -> dict:
        return {
            "assets_by_stage": await self.repos.governance_assets.count_by_stage(tenant_id),
            "pending_approvals": await self.repos.approval_requests.count_pending(tenant_id),
        }
