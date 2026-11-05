# AIOS Enterprise Analytics, Business Intelligence & Executive Reporting Platform

Package `analytics_platform`, table prefix `an_`. Delivered as `aios-analytics-platform.zip`.

## What this is

The single source of analytics truth for the AI Operating System: a Data Warehouse and Metrics Registry that ingests raw events from all 16 declared platform data sources, an Aggregation Engine that rolls those events into real sum/avg/min/max/count/p50/p95/p99 statistics across four analytics domains and four time periods, a direction-aware KPI Engine, a Reporting Platform covering all nine report types the prompt specifies, a Forecasting Engine with three real statistical methods plus anomaly detection, a rule-based Recommendation Engine across all eight optimization categories, a Visualization & Dashboard Platform spanning all eleven visualization types, Security & Governance (RBAC, row-level and column-level security, an audit log, and multi-hop data lineage traversal), and an Observability layer that watches the platform's own usage, query performance, forecast accuracy, and recommendation acceptance. Built with the same clean/layered architecture as every other AIOS platform: pure-Python domain entities with guarded state machines, a repository/unit-of-work layer, service layer, and a FastAPI REST layer.

**Out of scope by design:** no Testing & Quality Engineering Platform, no Documentation Platform, no Release Candidate.

## Architecture

Identical pattern to every sibling AIOS platform:

- `domain/` — pure-Python entities (`ReportRun`, `ForecastJob`, `Recommendation`, `Dashboard`, `DataExportJob`) with guarded `_transition()` state machines over enums, no ORM imports. Simpler status-only resources (metric/KPI definitions, security rules, role grants) are guarded directly in-service instead, the same precedent set by every other platform's own "simple status field" resources.
- `models/` — SQLAlchemy 2.0 async ORM models, 22 tables across 10 files (`an_` prefix).
- `repositories/` — one repository per model plus a `RepositoryRegistry` unit-of-work that lazily shares a single `AsyncSession`.
- Service modules — one directory per domain, each holding the orchestrating business logic.
- `an_api/` — FastAPI Application Factory, versioned routers (80 routes across 9 route groups) + an unversioned `/health` probe, a shared exception-handler layer mapping the 46-class domain exception hierarchy to HTTP status codes, and lightweight ORM→dict serialization.
- `dependencies/` — FastAPI dependency wiring (DB session → `RepositoryRegistry` → services), plus `X-Tenant-Id`/`X-User-Id` header extraction. This platform expects to sit behind an already-authenticated caller (in practice, the Identity Platform).

## Module breakdown

**Data Warehouse & Metrics Registry** (`warehouse/`) — a metric catalog (get-or-create by key, validated against the platform's data-source/unit/aggregation-type vocabularies) and raw event ingestion (single and batch, with a configurable batch cap and a retention sweep), the landing zone every other module reads from.

**Aggregation & Analytics Engine** (`analytics/`) — a generic rollup table spanning all four analytics domains the prompt specifies (business, ai, financial, performance) and all four rollup periods (hourly, daily, weekly, monthly), computed with real (non-stubbed) sum/avg/min/max/count and linear-interpolation percentile (p50/p95/p99) math over raw event values, upserted per `(metric_key, domain, period, period_start)`. Four domain-locked service facades (`BusinessAnalyticsService`, `AiAnalyticsService`, `FinancialAnalyticsService`, `PerformanceAnalyticsService`) wrap the shared engine so a caller can never accidentally tag a "business" rollup as "ai".

**KPI Engine** (`kpis/`) — KPI definitions across the seven scopes the prompt specifies (custom, organization, workspace, engineering, ai, business, executive), each carrying a target plus optional warning/critical thresholds and a `higher_is_better` direction flag, so "breached" means the right thing whether the metric should go up (retention) or down (error rate). Snapshot history gives every KPI a real trend line (`up`/`down`/`flat`), not just a current value.

**Reporting Platform** (`reports/`) — report definitions across all nine report types the prompt specifies (executive, engineering, ai_performance, security, financial, compliance, operational, usage, custom), each with a sensible default pull set of analytics domains and KPI scopes that a definition's own `config` can override — this is what lets "custom" reports (and any other type an org wants to reshape) work without a schema change. Report runs are guarded queued → generating → completed/failed, and assemble real content from already-computed rollups and KPI snapshots (plus an audit-log summary for security/compliance reports) rather than returning a stub payload.

**Forecasting Engine** (`forecasting/`) — three real, dependency-free statistical methods (moving average, linear regression, exponential smoothing) projecting real historical rollup data forward across all eight forecast types the prompt specifies, plus a z-score anomaly scan over the same history. Each forecast type pulls from a sensible default analytics domain/rollup period; jobs are guarded queued → running → completed/failed and fail closed (via `InsufficientHistoryError`) rather than fabricating a forecast from too little data.

**Recommendation Engine** (`recommendations/`) — rule-based recommendations across all eight optimization categories the prompt specifies, derived from two real signal sources: KPI health (a breached or at-risk KPI in a given scope maps to a specific category and impact level) and forecast results (anomalies and steep growth trends each produce their own recommendation). Guarded open → accepted/dismissed → implemented, with every transition recorded as an outcome row for acceptance-rate analytics.

**Visualization & Dashboard Platform** (`dashboards/`) — dashboards guarded draft → published ↔ archived, widgets across all eleven visualization types the prompt specifies (a generic row with free-form `query_config` JSON rather than a table per viz type), capped per dashboard by a configurable max-widgets setting, and saved views — named filter/layout presets a user can create and return to, the self-service piece that lets organizations reshape a dashboard without an engineering change.

**Security & Governance** (`security/`) — a four-level role hierarchy (viewer/analyst/editor/admin) with a real hierarchy-aware permission check other modules can call, row-level security (tenant-scoped, workspace-scoped, or disclosed-unrestricted) that fails toward the safer default when unconfigured, column-level security that redacts restricted columns unless the caller's role clears the bar, an append-only audit log, and multi-hop data lineage traversal (breadth-first, depth-capped, cycle-safe) so any number on a dashboard can be traced back to the raw events that produced it.

**Observability** (`observability/`) — usage-event tracking across the six event types the prompt specifies plus a retention sweep, query-performance tracking (slow-query detection, average duration), forecast-accuracy tracking (predicted vs. actual once a horizon has passed, with a disclosed zero-division convention), and recommendation-outcome analytics (acceptance rate, outcome breakdown) — the "is this platform's own output actually useful" feedback loop.

## Concurrency

Three commit-spanning `asyncio.Lock` sequences, the same pattern established across every other AIOS platform for check-then-act races that span multiple statements (separate callers own separate DB connections; SQLite only makes a write visible to others once committed — and the lock must be held until that commit happens, not just until the row is flushed, or a waiting caller can still observe pre-commit state):

- `MetricRegistryService.register_metric` — get-or-create by metric key, locked per `tenant_id:key`.
- `KpiService.register_kpi` — get-or-create by name within scope, locked per `tenant_id:scope:name`.
- `ReportDefinitionService.register_report` — get-or-create by name within report type, locked per `tenant_id:report_type:name`.

All three are proven under real concurrent load in `tests/performance/test_concurrency.py`, which races genuine independent DB connections via `asyncio.gather` (never the rollback-isolated test fixture) and asserts no duplicate rows and no lost writes. Fixing this also surfaced a real test-isolation bug: exercising a commit-spanning-lock method through the rollback-isolated `repos` fixture durably commits everything written earlier in that test, so two report-generator tests that happened to share a metric key started leaking rollup history into each other — fixed by giving each test its own metric key, the same discipline `tests/conftest.py`'s `db_session` fixture docstring already calls out.

## Testing

157 tests, ruff clean. Test suite mirrors the module breakdown: `tests/repository` (schema smoke test), `tests/warehouse`, `tests/analytics`, `tests/kpis`, `tests/reports`, `tests/forecasting`, `tests/recommendations`, `tests/dashboards`, `tests/security`, `tests/observability`, `tests/an_api` (13 end-to-end HTTP tests driving every domain through the real FastAPI app), `tests/performance` (concurrency stress).

## Disclosed scope boundaries

Consistent with every other AIOS platform's honest-gap posture:

- This is a control plane and computation engine, not a live ETL puller — it ingests events pushed to it (via `EventIngestionService`) rather than reaching into Authentication, Organizations, Workflows, etc. and pulling their data itself. The 16 data sources the prompt specifies are a validated vocabulary metric definitions declare against, not live connectors.
- Rollups, forecasts, and reports are computed against whatever's in this platform's own SQLite-by-default warehouse tables. "Scale to billions of events" is an architectural property of the rollup-not-raw-scan design (reads hit pre-aggregated `an_metric_rollups`, not raw `an_metric_events`), not a claim this reference implementation has been load-tested at that volume — a production deployment would put a real OLAP store (ClickHouse, BigQuery, Snowflake) behind the same service interfaces.
- `an_export_jobs` and the `DataExportJob` domain entity exist in the schema (a guarded queued → running → completed/failed job, mirroring every other job-style resource in this platform), but no export-generation service or API was built against it in this delivery — exporting a report/dashboard to a downloadable file is schema-ready, not implemented.
- Forecast methods are three real, disclosed-simple statistical techniques (moving average, linear regression, simple exponential smoothing) — no ARIMA, Prophet, or ML-based forecasting.
- Recommendation generation is rule-based off two signal sources (KPI health, forecast results) — not an ML recommender.
- Column-level security redacts restricted columns from an already-fetched row dict; it does not rewrite SQL to exclude those columns at the query layer.
- Forecast accuracy's zero-division convention (0% error if both predicted and actual are exactly zero, 100% otherwise) is a disclosed choice, not a statistically derived one.

## Running it

```bash
pip install -r requirements.txt
uvicorn analytics_platform.an_api.application_factory:create_app --factory --reload
```

Every request needs an `X-Tenant-Id` header; `X-User-Id` is optional (system-triggered checks legitimately have no human actor). Interactive docs at `/docs`.
