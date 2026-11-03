# AIOS Enterprise Testing, Quality Engineering & Reliability Platform

Phase 19 of the AIOS build. Package `quality_platform`, table prefix `qa_`. Delivered as `aios-quality-platform.zip`.

## What this is

The quality backbone of the AI Operating System: test automation across a 15-type test pyramid (unit through acceptance, including agent/prompt/memory/tool/workflow tests specific to AI systems), an AI evaluation regression engine that compares fresh evaluation scores against stored baselines across 13 AI-quality dimensions, a performance testing engine (load/stress/spike/soak/scalability/concurrency) with bottleneck/capacity analysis, a chaos engineering platform across 12 failure types with blast-radius safety caps and recovery tracking, a security testing engine across 11 test types with severity-based gate-blocking, API and workflow validation, reliability engineering (SLOs, error budgets, 8 reliability metric types), a quality gates & coverage platform (8 check types, 9 coverage types), failure pattern tracking and risk scoring, a release certification engine that combines weighted category scores into a deployment decision, and quality observability (trend snapshots across 8 metric types). Built with the same clean/layered architecture as every prior AIOS platform: pure-Python domain entities with guarded state machines, a repository/unit-of-work layer, service layer, and a FastAPI REST layer.

**Out of scope by design:** the documentation platform and release packaging (separate services).

## Architecture

Identical pattern to every sibling AIOS platform:

- `domain/` — a shared `JobStatus` enum (queued → running → completed/failed) reused across every job-style resource in this platform rather than re-declared per module, since the transition semantics are identical everywhere. A shared `_GuardedJob` mixin implements the transition guard once; five job-style resources (`TestRun`, `RegressionScan`, `PerformanceTestRun`, `ChaosExperiment`, `CertificationRun`) get a dedicated dataclass entity via multiple inheritance. Two more job-style resources (`SecurityScan`, `WorkflowValidationRun`) are simple enough that their status is guarded directly in-service instead, the same "simple status field" precedent set by every prior platform.
- `models/` — SQLAlchemy 2.0 async ORM models, 23 tables across 11 files (`qa_` prefix).
- `repositories/` — one repository per model plus a `RepositoryRegistry` unit-of-work that lazily shares a single `AsyncSession`.
- Eleven service-module directories, one per domain, each holding the orchestrating business logic plus (where the domain has real classification/scoring rules) a pure-function `*_rules.py` file with no DB or service imports, so the decision logic is trivially unit-testable in isolation from persistence.
- `qa_api/` — FastAPI Application Factory, versioned routers (78 routes across 11 route groups) + an unversioned `/health` probe, a shared exception-handler layer mapping the 49-class domain exception hierarchy to HTTP status codes, and lightweight ORM→dict serialization.
- `dependencies/` — FastAPI dependency wiring (DB session → `RepositoryRegistry` → services), plus `X-Tenant-Id`/`X-User-Id` header extraction. This platform expects to sit behind an already-authenticated caller (in practice, the Identity Platform).

## Module breakdown

**Test Management & Automation** (`testing/`) — suites and cases spanning the 15-type test pyramid (unit, component, integration, contract, API, database, UI, workflow, agent, prompt, memory, tool, system, e2e, acceptance), a guarded test-run lifecycle, per-case result recording, and flaky-test detection: a case is reclassified as "flaky" the moment its recent pass/fail history crosses `test_run_flaky_threshold` transitions within `test_run_history_window` results.

**AI Quality / Evaluation Regression Engine** (`ai_quality/`) — baselines and raw evaluation scores per (dimension, subject) across the 13 AI-quality dimensions the prompt specifies (prompt accuracy, reasoning quality, planning quality, memory retrieval, tool selection, workflow execution, agent collaboration, groundedness, hallucination rate, citation quality, instruction following, consistency, structured output), and a regression-scan job that classifies drift (none/minor/major/critical) in multiples of `ai_quality_regression_threshold_pct` — severity is only ever assigned on a drop, never on an improvement.

**Performance Testing Engine** (`performance/`) — a guarded run lifecycle across the six performance test types (load, stress, spike, soak, scalability, concurrency), benchmark result recording across seven metric types (latency p50/p95/p99, throughput, error rate, CPU/memory utilization), and bottleneck/capacity analysis (resource saturation, error-rate breach, tail-latency amplification).

**Chaos Engineering Platform** (`chaos/`) — a guarded experiment lifecycle across the 12 failure types the prompt specifies (node, database, network latency, packet loss, service shutdown, worker, queue, cache, storage, GPU, external API, region), rejecting any experiment whose blast radius exceeds `chaos_max_blast_radius_pct` before a single statement is committed, and recovery tracking (recovered flag + recovery time).

**Security Testing Engine** (`security_testing/`) — a guarded scan lifecycle across the 11 security test types (authentication, authorization, RBAC, prompt injection, jailbreak, secrets, API security, dependency scanning, container security, infrastructure security, compliance), finding recording by severity, and gate-blocking when a critical finding is recorded and `security_critical_finding_blocks_gate` is set.

**API & Workflow Validation** (`validation/`) — synchronous API validation checks (schema, request, response, contract, backward/version/SDK compatibility — these are instantaneous pass/fail checks, not jobs) and a guarded workflow-validation run lifecycle across the nine correctness dimensions the prompt specifies (logic, node execution, parallel execution, retries, compensation, timeout handling, failure recovery, approval chains, human-in-the-loop).

**Reliability Engineering** (`reliability/`) — SLO definitions per service with a computed status (meeting/at_risk/breached, classified against `target_pct`), reliability metric snapshots across the eight types the prompt specifies (availability, reliability, durability, error budget, MTTD, MTTR, MTBF, recovery success rate), and error-budget-remaining arithmetic.

**Quality Gates & Coverage Platform** (`quality_gates/`) — a guarded release-gate lifecycle scoring the percentage of recorded checks (across the eight check types the prompt specifies) that passed against `quality_gate_min_score` — a gate with no recorded checks scores 0 and fails closed — plus coverage snapshots across the nine coverage types the prompt specifies (code, API, workflow, prompt, agent, model, dataset, UI, integration).

**Failure Analysis & Risk Analysis** (`failure_analysis/`) — recurring failure pattern tracking (regression, root cause, flaky test, performance regression, memory leak, concurrency issue, infrastructure issue) with an occurrence counter that increments on recurrence, and risk assessment scoring a subject from caller-supplied 0-100 factor readings, classified into low/medium/high/critical against `risk_high_threshold`/`risk_critical_threshold`.

**Release Certification Engine** (`certification/`) — a guarded certification-run lifecycle that combines whichever quality/reliability/security/performance/AI-quality scores are supplied into a weighted overall score (weights renormalized over just the supplied categories, via `certification_score_weights`) and a deployment decision (approved / approved with conditions / rejected) against `certification_min_score_for_approval`.

**Observability** (`observability/`) — trend snapshot recording/querying across the eight metric types the prompt specifies (test executions, quality, regression, coverage, failure, performance, reliability, release), plus trend-direction analysis (improving/stable/declining) by comparing older-half vs. newer-half averages of a series.

## Concurrency

Five commit-spanning `asyncio.Lock` sequences, the same pattern established across every prior AIOS platform for check-then-act races that span multiple statements (separate callers own separate DB connections; SQLite only makes a write visible to others once committed — and the lock must be held until that commit happens, not just until the row is flushed, or a waiting caller can still observe pre-commit state):

- `TestSuiteService.register_suite` — get-or-create by test suite name, locked per `tenant_id:name`.
- `BaselineService.set_baseline` — upsert (create-or-update) by dimension+subject, locked per `tenant_id:dimension:subject_ref`.
- `SloService.register_slo` — get-or-create by SLO name, locked per `tenant_id:name`.
- `QualityGateService.create_gate` — get-or-create by release+name, locked per `tenant_id:release_ref:name`.
- `FailurePatternService.record_occurrence` — get-or-increment by pattern type+subject, locked per `tenant_id:pattern_type:subject_ref`; this one additionally proves no *lost updates* under concurrency (15 concurrent callers must produce an occurrence count of exactly 15, not fewer).

All five are proven under real concurrent load in `tests/performance/test_concurrency.py`, which races genuine independent DB connections via `asyncio.gather` (never the rollback-isolated test fixture) and asserts no duplicate rows and no lost writes.

## Testing

155 tests, ruff clean. Test suite mirrors the module breakdown: `tests/repository` (schema smoke test), `tests/testing`, `tests/ai_quality`, `tests/performance` (bottleneck rules, performance run service, and the concurrency stress suite), `tests/chaos`, `tests/security_testing`, `tests/validation`, `tests/reliability`, `tests/quality_gates`, `tests/failure_analysis`, `tests/certification`, `tests/observability`, `tests/qa_api` (15 end-to-end HTTP tests driving every domain through the real FastAPI app).

## Self-review

The prompt asks whether this platform can actually deliver on its premise. Going through each question honestly:

*Can every subsystem be verified automatically?* Yes for what's built: test runs, performance runs, chaos experiments, security scans, API/workflow validation, and certification runs are all driven through a real guarded job lifecycle with programmatic start/complete/fail transitions and machine-readable results (summaries, bottleneck findings, findings-by-severity, pass/fail checks) — nothing here requires a human to eyeball a log. What isn't automatic is the *content* of each check: this platform is the control plane and scoring/classification layer, not a test executor. It expects a caller (a CI job, an agent harness, a load-testing tool) to actually run the check and report the result back through `record_result`/`record_finding`/`record_check`/`benchmark result recording` — the same disclosed boundary every prior AIOS platform draws around "we orchestrate and score, we don't reimplement the underlying tool."

*Are regressions detected before release?* The regression engine compares every fresh evaluation against a stored baseline and classifies severity before a human has to notice a drop, and `assert_no_regression` gives a caller (a CI gate, a certification run) a hard failure path for major/critical drift. Whether it happens *before* release depends on the caller wiring a regression scan into their release pipeline ahead of the certification run — this platform makes that possible and cheap, but doesn't force the ordering, since it has no opinion on any specific external CI system.

*Are failures reproduced consistently?* Flaky-test detection (`is_case_flaky`) and failure-pattern tracking (`FailurePatternService`) both work off the same principle: a single failure is just a data point, but a *recurring* one — occurrences crossing `failure_pattern_min_occurrences`, or a test's pass/fail history crossing `test_run_flaky_threshold` transitions — gets flagged as a pattern worth root-causing rather than re-running and hoping. The platform tracks recurrence; it doesn't itself re-execute a failing test to prove determinism, since that's the test runner's job, not the quality platform's.

*Is reliability measured objectively?* SLO status is computed from recorded metric snapshots against a numeric target, not a subjective judgment call, and error-budget-remaining is a pure arithmetic function of the same two numbers. The honest caveat: "meeting/at_risk/breached" needs real availability data flowing in via `record_snapshot` — an SLO nobody's reporting metrics against can't be evaluated (this raises a `ValidationError` rather than silently reporting a fake status).

*Do quality standards improve continuously?* The trend service gives every metric family (quality, regression, coverage, failure, performance, reliability, release, test executions) a real time series and a direction classifier, so "is this getting better or worse" is answerable from data rather than anecdote. Whether standards *actually* improve is a human/organizational outcome this platform can measure and surface, not one it can force — the same honest boundary observability platforms in general have to draw.

*Can the platform guarantee production-grade releases?* No platform can *guarantee* an outcome that depends on humans acting on the data — but this one gives a release nothing to hide behind: certification combines quality, reliability, security, performance, and AI-quality signals into one weighted score and an explicit approved/approved-with-conditions/rejected decision; quality gates fail closed with zero evidence; a critical security finding can be configured to block the gate outright. The gap between "this platform says the data doesn't support shipping" and "the release ships anyway" is a human process decision outside this platform's control, and every prior AIOS platform in this series has drawn that same line rather than overclaiming enforcement it can't back up.

## Disclosed scope boundaries

Consistent with every prior AIOS platform's honest-gap posture:

- This is a control plane and scoring/classification layer, not a test executor — it does not run pytest, load-test tooling, chaos-injection agents, or security scanners itself. Callers report results back through `record_result`/`record_finding`/`record_check`/benchmark recording.
- The medium/low risk-level boundary (`risk_rules.classify_risk_level`) is derived as half of `risk_high_threshold` rather than adding a third setting nobody asked for — disclosed in the module docstring rather than hidden.
- The SLO at-risk margin (`slo_rules.DEFAULT_AT_RISK_MARGIN_PCT = 0.5`) and the certification approved-with-conditions band (`certification_rules.DEFAULT_CONDITIONAL_BAND_PCT = 10.0`) are the same kind of disclosed default — configurable via the function's keyword argument, not hardcoded assumptions hidden inside a black box.
- `certification_rules.compute_overall_score` renormalizes weights over whichever category scores are actually supplied, rather than treating a missing category as a zero that silently drags the score down for a reason unrelated to quality.
- API keys, secrets, and credentials are out of scope for this platform entirely — it assumes the Security Platform and Identity Platform handle those; this platform only records *findings about* security posture (via `SecurityScanService`), it doesn't manage secrets itself.
- `trend_rules.compute_trend_direction` compares older-half vs. newer-half averages, not a real regression/slope fit — a disclosed simplification, since a proper trend line needs a charting/stats library this control plane doesn't depend on.

## Running it

```bash
pip install -r requirements.txt
uvicorn quality_platform.qa_api.application_factory:create_app --factory --reload
```

Every request needs an `X-Tenant-Id` header; `X-User-Id` is optional (system-triggered checks legitimately have no human actor). Interactive docs at `/docs`.
