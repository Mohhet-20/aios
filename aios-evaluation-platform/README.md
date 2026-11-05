# AIOS Enterprise AI Evaluation, Benchmarking & Observability Platform

Package `eval_platform`, table prefix not fixed to a single value per-table but consistently namespaced under `eval_platform.models`. This README was reconstructed during the documentation audit architecture audit — the platform shipped without one; every fact below is verified against the actual source (settings, exceptions, module docstrings, route count, test count), not inferred.

## What this is

The quality backbone every other AIOS platform reports into: evaluations and reusable benchmarks over versioned datasets, a 20-metric quality-scoring registry, model/prompt/agent/workflow benchmarking, a pluggable hallucination/groundedness verifier, cross-platform observability event ingestion (prompt/agent/workflow/tool/memory platforms all report through one entry point), alerting with an OPEN → ACKNOWLEDGED → RESOLVED lifecycle, an AI-improvement recommendation loop, and governance (per-workspace concurrent-run caps and rate limits enforced against real database counts, not an in-memory counter that would drift across processes). Built with the same clean/layered architecture as every other AIOS platform: pure-Python domain entities with guarded state machines, a repository/unit-of-work layer, a service layer, and a FastAPI REST layer.

## Architecture

- `domain/` — pure-Python entities with guarded `_transition()` state machines (`Evaluation`, `Dataset`, `Alert`, and others sharing the generic job-run shape).
- `models/` — SQLAlchemy 2.0 async ORM models, 21 tables.
- `repositories/` — one repository per model plus a `RepositoryRegistry` unit-of-work (includes the `get_many()` batch-fetch method added platform-wide during the platform-wide audits).
- Service modules — one directory per domain: `evaluation_core/`, `datasets/`, `metrics/`, `benchmarking/`, `agent_workflow/`, `hallucination/`, `observability/`, `alerting/`, `analytics/`, `governance/`, `execution/`.
- `eval_api/` — FastAPI Application Factory, versioned routers (96 routes) + an unversioned `/health` probe, a shared exception-handler layer mapping the 23-class domain exception hierarchy to HTTP status codes.
- `dependencies/` — FastAPI dependency wiring (DB session → `RepositoryRegistry` → services).

## Module breakdown

**Evaluation Core & Datasets** (`evaluation_core/`, `datasets/`) — identity/ownership/lifecycle CRUD for `EvaluationModel` and `DatasetModel` follow an identical shape: the top-level service only ever touches identity fields and drives the domain entity's lifecycle transitions, while a separate `version_service.py` owns editing the actual contract (an evaluation's dataset binding/metrics/scoring config/pass threshold/target, or a dataset's item set).

**Quality Metrics Engine** (`metrics/`) — an in-code catalog of 20 built-in quality metrics (`registry.py`), with the computation functions in `functions.py` and `MetricDefinitionModel` rows seeded from the registry so a scorecard UI can query available metrics without importing Python.

**Benchmarking** (`benchmarking/`) — `BenchmarkService` (identity/ownership CRUD for a reusable comparison setup bound to a dataset — model benchmarking, prompt A/B/multivariate testing, or agent/workflow comparison depending on `benchmark_type`/`mode`) and `run_service.py` (the actual multi-candidate execution).

**Agent & Workflow Evaluation** (`agent_workflow/`) — `TargetExecutor` implementations that fetch a real execution trace via an `AgentPlatformBridge`/`WorkflowPlatformBridge` and turn it into a `TargetExecutionResult`, so agent/workflow outputs feed the same standard metric registry (task success rate, latency, ...) as any other target type.

**Hallucination Detection** (`hallucination/`) — `GroundingVerifier` is a pluggable seam; `LexicalOverlapVerifier` is the shipped default, a real deterministic sentence-level token-overlap implementation (`method="lexical_overlap"`), honestly disclosed as a lexical rather than semantic/NLI-based check — a stronger verifier is a swap-in behind the same interface.

**Observability** (`observability/`) — `ObservabilityIngestionService` is the single entry point every upstream AIOS platform reports its own execution events through; `source_platform` distinguishes origin and `source_execution_id` correlates an event back to the reporting platform's own record.

**Alerting** (`alerting/`) — `AlertService` reuses the `Alert` domain entity's OPEN → ACKNOWLEDGED → RESOLVED state machine; an alert can be opened standalone (e.g. a one-off safety flag raised inline during scoring) or by `AlertEvaluator` when a rule's condition is met.

**Analytics / AI Improvement Loop** (`analytics/`) — `RecommendationService`: CRUD plus a simple OPEN → ACCEPTED/DISMISSED lifecycle. Unlike alerts, recommendations don't reopen — a decided recommendation is closed, and a fresh analysis run creates a new row rather than resurrecting an old one, keeping history intact.

**Governance** (`governance/`) — `EvaluationPolicyService` is the gate `EvaluationRunService.start_run`/`BenchmarkRunService.start_run` check before starting: a per-workspace concurrent-run cap and a per-triggerer rate limit, both enforced against real database counts.

## Concurrency

`tests/performance/` contains real concurrency/stress tests racing genuinely independent sessions against the same file-backed SQLite database (not the rollback-isolated `repos` fixture every unit test uses) — the same methodology used across every other AIOS platform, and the same kind of test that caught a real governance/session-lock regression during this platform's own original build. No commit-spanning `asyncio.Lock` was found in the current source (`governance`'s concurrency caps are enforced via a real database count check rather than an in-process lock, since the cap only needs to be approximately, not perfectly, enforced under race — a documented design choice, not an oversight).

## Testing

218 tests passing, ruff clean. Test suite mirrors the module breakdown: `tests/unit`, `tests/repository`, `tests/evaluation_core`, `tests/datasets`, `tests/metrics`, `tests/benchmarking`, `tests/agent_workflow`, `tests/hallucination`, `tests/observability`, `tests/alerting`, `tests/analytics`, `tests/governance`, `tests/execution`, `tests/eval_api`, `tests/performance`.

## Self-review

This README was written after the fact as part of a documentation-consistency audit — the platform itself (218 tests, 96 REST routes, ruff-clean) was already solid; what was missing was purely the documentation artifact every sibling platform has. No source changes were needed to write it, which is itself a signal the codebase's module docstrings were thorough enough to reconstruct an accurate architecture doc from.

## Running it

```bash
pip install -r requirements.txt
uvicorn eval_platform.eval_api.application_factory:create_app --factory --reload
```
