"""Report content assembly: turns a report definition's type/config
into a real JSON payload pulled from already-computed rollups (Task
#264) and KPI snapshots (Task #265), plus an audit-log summary for the
two report types that need one. Each report type has a sensible
default set of analytics domains / KPI scopes to pull from, which a
definition's own `config` can override — this is what lets "custom"
reports (and any other type an org wants to reshape) work without a
schema change.

This module contains only pure(ish) read/assemble logic — no run
lifecycle transitions, no persistence of the result. `ReportRunService`
is responsible for wiring this into the guarded queued -> generating
-> completed/failed lifecycle."""
from __future__ import annotations


from analytics_platform.repositories.registry import RepositoryRegistry
from analytics_platform.clock import utc_now

# Each report type's default pull set. A definition's `config` dict may
# override any of these keys (`domains`, `kpi_scopes`, `metric_keys`,
# `include_audit_summary`) to reshape what gets assembled without a
# schema or code change — this is how "custom" reports work.
REPORT_TYPE_DEFAULTS: dict[str, dict] = {
    "executive": {"domains": ["business", "ai", "financial", "performance"], "kpi_scopes": ["executive"], "include_audit_summary": False},
    "engineering": {"domains": ["performance"], "kpi_scopes": ["engineering"], "include_audit_summary": False},
    "ai_performance": {"domains": ["ai"], "kpi_scopes": ["ai"], "include_audit_summary": False},
    "security": {"domains": [], "kpi_scopes": [], "include_audit_summary": True},
    "financial": {"domains": ["financial"], "kpi_scopes": ["business"], "include_audit_summary": False},
    "compliance": {"domains": [], "kpi_scopes": [], "include_audit_summary": True},
    "operational": {"domains": ["performance"], "kpi_scopes": ["engineering"], "include_audit_summary": False},
    "usage": {"domains": ["business"], "kpi_scopes": [], "include_audit_summary": False},
    "custom": {"domains": [], "kpi_scopes": [], "include_audit_summary": False},
}


def _resolve_pull_set(report_type: str, config: dict) -> dict:
    base = dict(REPORT_TYPE_DEFAULTS.get(report_type, REPORT_TYPE_DEFAULTS["custom"]))
    for key in ("domains", "kpi_scopes", "metric_keys", "include_audit_summary", "period"):
        if key in config:
            base[key] = config[key]
    base.setdefault("period", "daily")
    return base


class ReportGeneratorService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def _metric_section(self, tenant_id: str, *, domains: list[str], metric_keys: list[str] | None, period: str) -> list[dict]:
        if not domains:
            return []
        if metric_keys is None:
            definitions = await self.repos.metric_definitions.list_for_tenant(tenant_id)
            metric_keys = [d.key for d in definitions]
        section: list[dict] = []
        for key in metric_keys:
            for domain in domains:
                rollups = await self.repos.metric_rollups.list_for_metric(tenant_id, key, domain=domain, period=period, limit=50)
                if not rollups:
                    continue
                latest = rollups[-1]
                section.append({
                    "metric_key": key,
                    "domain": domain,
                    "period": period,
                    "value": latest.value,
                    "sample_count": latest.sample_count,
                    "period_start": latest.period_start.isoformat(),
                })
        return section

    async def _kpi_section(self, tenant_id: str, *, kpi_scopes: list[str]) -> list[dict]:
        if not kpi_scopes:
            return []
        section: list[dict] = []
        for scope in kpi_scopes:
            kpis = await self.repos.kpi_definitions.list_for_tenant(tenant_id, scope=scope)
            for kpi in kpis:
                snapshots = await self.repos.kpi_snapshots.list_for_kpi(tenant_id, kpi.id, limit=1)
                latest = snapshots[0] if snapshots else None
                section.append({
                    "kpi_id": kpi.id,
                    "name": kpi.name,
                    "scope": scope,
                    "target_value": kpi.target_value,
                    "current_value": latest.value if latest else None,
                    "health": latest.health if latest else "unknown",
                })
        return section

    async def _audit_summary(self, tenant_id: str) -> dict:
        entries = await self.repos.audit_log.list_recent(tenant_id, limit=200)
        by_action: dict[str, int] = {}
        for entry in entries:
            by_action[entry.action_type] = by_action.get(entry.action_type, 0) + 1
        return {"total_events": len(entries), "by_action_type": by_action}

    async def build_payload(self, tenant_id: str, *, report_type: str, config: dict) -> dict:
        pull = _resolve_pull_set(report_type, config)
        payload: dict = {
            "report_type": report_type,
            "tenant_id": tenant_id,
            "generated_at": utc_now().isoformat(),
            "period": pull["period"],
            "metrics": await self._metric_section(
                tenant_id, domains=pull["domains"], metric_keys=pull.get("metric_keys"), period=pull["period"],
            ),
            "kpis": await self._kpi_section(tenant_id, kpi_scopes=pull["kpi_scopes"]),
        }
        if pull.get("include_audit_summary"):
            payload["audit_summary"] = await self._audit_summary(tenant_id)
        return payload
