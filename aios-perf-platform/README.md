# AIOS Enterprise Performance Optimization, Cost Intelligence & Scalability Platform

Phase 22 of the AIOS build. Package `perf_platform`, table prefix `perf_`. Delivered as `aios-perf-platform.zip`.

This phase was explicitly **not** a new-feature phase — it is a repository-wide performance audit followed by a dedicated optimization/cost-intelligence toolkit. Two deliverables came out of it, covered in order below: (1) real fixes applied directly to the existing 20 AIOS repositories, and (2) this new platform, which gives every other platform a shared caching layer, LLM cost-intelligence router, cost/budget engine, auto-optimization recommendation engine, and performance observability.

## Part 1 — Repository-wide audit and fixes

The audit was static and evidence-based: grep/pattern search across all 20 `aios-*` repositories for the bottleneck classes the prompt named (N+1 queries, missing indexes, blocking calls in async code, unbounded queries), followed by targeted, test-verified fixes — no speculative rewrites, no architecture changes.

**N+1 query elimination.** `SQLAlchemyRepository.get_many(ids)` (batch-fetch by primary key in one query, order-preserving, missing ids silently skipped) was added to the base repository shared by all 18 platform packages that have one (`release_platform`, `docs_platform`, `security_platform`, `tool_platform`, `memory_platform`, `identity_platform`, `prompt_platform`, `collaboration_platform`, and 10 others). 8 confirmed N+1 call sites — each a `for id in ids: await repo.get(id)` loop — were rewritten to call it instead:

- `tool_platform.discovery.DiscoveryService.recently_used` and `.list_favorites`
- `memory_platform.knowledge_graph.GraphService.neighbors`
- `prompt_platform.prompt_registry.LibraryService.list_favorites` and `.list_collection_prompts`
- `collaboration_platform.search.SearchService.search_by_tag`
- `identity_platform.authorization.AuthorizationService.has_permission` and `.effective_permissions` — the highest-value fix of the eight, since these sit on the hot path of every permission check across the platform (a request authorizing against N role assignments previously issued N+1 queries; now issues 2)

Every affected platform's full test suite was re-run after each fix (tool-platform: 258 passed; memory-platform: 182 passed; prompt-platform: full suite passed; collaboration-platform: 71 passed; identity-platform: 179 passed), plus ruff on each touched file, before moving on.

**Missing indexes.** `collaboration_platform`'s `workspace_id` foreign-key columns — the primary filter predicate on every `list_for_workspace`-shaped query in that platform (verified by grepping every repository for `.where(Model.workspace_id == workspace_id)` before touching anything, so index was only added to columns proven to be hot filter predicates, not speculatively) — were missing `index=True` across 9 columns in `activity.py`, `asset.py`, `governance.py`, `productivity.py`, and `workspace.py`. All 9 were indexed; full suite (71 tests) and ruff re-confirmed clean afterward.

**What was checked and found clean.** Blocking `time.sleep`/synchronous-HTTP calls inside async request paths (none found outside test fixtures and one legitimate sync SDK client's rate-limit backoff); unbounded list endpoints (the shared base repository already defaults every `list()` to `limit=100`, so this was structurally already bounded platform-wide, not something this pass needed to fix).

## Part 2 — perf_platform

### What this is

A shared performance-optimization and cost-intelligence toolkit the rest of AIOS can build on: multi-level caching (an in-process L1 LRU/TTL cache plus a DB-backed L2 layer across all 11 declared cache layers), LLM cost-intelligence model routing (deterministic task-complexity-to-tier selection with org/workspace policy overrides and per-request cost estimation), real-time cost tracking and budget enforcement with threshold alerts, an auto-optimization recommendation engine that mines this platform's own cache/latency/routing/budget signals, and observability (latency percentiles, throughput, benchmark runs) plus a GPU pool inventory for scalability planning. Built with the same clean/layered architecture as every prior AIOS platform: pure-Python domain entities with guarded state machines, a repository/unit-of-work layer, a service layer, and a FastAPI REST layer.

**Out of scope by design:** no repository cleanup beyond the targeted fixes described above, no rewrites for cosmetic reasons, no packaging of the overall AIOS meta-project — this platform's own delivery follows the same standard packaging step every prior platform in the series has used.

### Architecture

- `domain/` — pure-Python entities (`BenchmarkRun`, `Recommendation`) with guarded `_transition()` state machines. `BenchmarkRun` shares the generic queued → running → completed/failed job shape every prior platform's job lifecycle uses. `Recommendation` has its own bespoke editorial lifecycle (proposed → accepted → applied, with reject/expire as alternate terminal states) since a cost/perf recommendation is proposed by the engine and then decided by a human or policy, not just run to completion.
- `models/` — SQLAlchemy 2.0 async ORM models, 12 tables across 6 files (`perf_` prefix).
- `repositories/` — one repository per model plus a `RepositoryRegistry` unit-of-work. `repositories/base.py` ships with `get_many()` from the start (see Part 1) rather than needing the audit fix applied to it separately.
- Service modules — one directory per domain (`caching/`, `routing/`, `cost_intelligence/`, `optimization/`, `observability/`, `scalability/`), most split into a pure `*_rules.py` (zero DB/service imports, unit-testable in isolation) plus a thin DB-backed `*_service.py` shell — the same split every prior platform used for `semver_rules.py`, `targeting_rules.py`, `license_rules.py`, etc.
- `perf_api/` — FastAPI Application Factory, versioned routers (40 routes across 6 route groups) + an unversioned `/health` probe, a shared exception-handler layer mapping the 31-class domain exception hierarchy to HTTP status codes, and lightweight ORM→dict serialization.
- `dependencies/` — FastAPI dependency wiring (DB session → `RepositoryRegistry` → 9 services), plus `X-Tenant-Id`/`X-User-Id` header extraction. This platform expects to sit behind an already-authenticated caller (in practice, the Identity Platform).

### Module breakdown

**Cache Platform** (`caching/`) — `LRUTTLCache` (`lru.py`) is a real, dependency-free, O(1) in-process L1 cache with TTL and LRU eviction, lazy expiry-on-access, and hit/miss/eviction counters — it's the actual hot-path implementation, not a simulation. `CacheService` composes it with a DB-backed L2 layer (`CacheEntryModel`) across all 11 declared layers (memory, redis, disk, cdn, prompt, embedding, response, workflow, model, feature, api) — "redis", "disk", "cdn" etc. are labels on the same DB-backed store today (see Disclosed scope boundaries), not different code paths, so wiring a real Redis/CDN client behind the same `get`/`set`/`invalidate` contract is a swap-in. `get_or_compute` is the cache-aside method most callers use. Per-(tenant, layer) hit/miss/hit-rate counters are tracked in `CacheStatModel` for the auto-optimization engine to read.

**LLM Cost-Intelligence Model Routing** (`routing/`) — `routing_rules.select_tier` is a pure, deterministic function: task complexity (trivial → expert) picks a baseline tier off an escalation ladder (small < medium < large < reasoning), a user-tier ceiling caps it (free tier can't reach reasoning by default), a tight latency budget (<800ms) downgrades one rung, vision/code requirements route directly to their specialty tier bypassing the ladder entirely, and an optional org/workspace `RoutingPolicy`'s `allowed_tiers` gracefully degrades the choice to the highest eligible rung (or raises `NoEligibleModelTierError` if nothing is eligible). Every decision is logged with its full reasoning string and an estimated cost via the pricing rules below.

**Cost Intelligence Engine** (`cost_intelligence/`) — `pricing_rules.py` computes token cost (per-tier, per-1K-token rates), infra cost (GPU/CPU/memory/storage/bandwidth, linear per-unit rates), budget utilization, and threshold-crossing detection — all pure functions over `Settings`-sourced rates (see Disclosed scope boundaries). `CostRecordService.record` writes an append-only cost ledger and inline-triggers `BudgetService.check_and_alert`, so a cost record that pushes an entity over a configured alert threshold (50/80/100% by default) fires immediately rather than waiting on a poll. `BudgetService.enforce` is a separate, opt-in hard stop for callers that want to block further spend once a budget is fully exhausted — `record()` itself never blocks, so a mis-configured budget can't cause an outage.

**Auto-Optimization Recommendation Engine** (`optimization/`) — `recommendation_rules.py` holds four pure signal-to-recommendation functions (low cache hit rate, high P99 latency, systematic model-tier over-provisioning, budget near exhaustion), each returning `None` when the signal doesn't warrant flagging. `RecommendationService` gathers the signals from this platform's own repositories, calls the rules, and deduplicates on (category, target_ref) among still-open recommendations so re-running generation doesn't spam duplicate rows for a condition that's still true. The model-tier over-provisioning check only fires once a mismatch has repeated at least 5 times — one occurrence isn't a pattern.

**Observability & Benchmarking** (`observability/`) — `metrics_rules.py` (nearest-rank percentile, mean, throughput, improvement-pct) backs `LatencyTrackingService` (P50/P90/P95/P99 + SLO pass/fail against `Settings`-configured thresholds) and `ThroughputTrackingService`. `BenchmarkService` drives the guarded `BenchmarkRun` lifecycle and computes `improvement_pct` from real baseline/optimized measurements — see the benchmark suite below for genuinely measured numbers, not asserted-true placeholders.

**GPU / Scalability** (`scalability/`) — `GpuPoolService` tracks pool inventory across 4 pool types (shared, dedicated, spot, reserved), per-pool utilization, and an `underutilized_pools` query that surfaces consolidation candidates for the cost-reduction conversation, supporting the GPU scheduling/autoscaling *architecture* the prompt asked for (see Disclosed scope boundaries for what a real scheduler integration would add).

### Concurrency

One commit-spanning `asyncio.Lock` sequence, the same pattern established across every prior AIOS platform for check-then-act races that span multiple statements (separate callers own separate DB connections; SQLite only makes a write visible to others once committed — the lock must be held until that commit happens, not just until the row is flushed, or a waiting caller can still observe pre-commit state):

- `CacheService.set` — get-or-create by (`tenant_id`, `layer`, `key`), locked per `tenant_id:layer:key`.

Proven under real concurrent load in `tests/performance/test_concurrency.py`, which races 15 genuine independent DB connections via `asyncio.gather` (never the rollback-isolated test fixture) and asserts no duplicate rows.

`BudgetService.set_budget`, `RoutingPolicyService.set_policy`, and `GpuPoolService.register_pool` all contain a similar get-or-create/upsert shape but are deliberately left unlocked: a budget/policy re-configuration race converges on whichever write lands last with no correctness violation (these are administrative writes, not high-frequency hot-path writes like a cache set), and a duplicate GPU pool row from a race would be a cosmetic data-quality issue an operator would notice immediately, not a silent correctness bug. Documented here rather than silently left unexamined.

### Testing

93 tests, ruff clean. Test suite mirrors the module breakdown: `tests/repository` (schema smoke test), `tests/caching`, `tests/cost_intelligence`, `tests/routing`, `tests/optimization`, `tests/observability`, `tests/scalability`, `tests/perf_api` (10 end-to-end HTTP tests driving every domain through the real FastAPI app), `tests/performance` (a genuinely measured cache-speedup benchmark, a genuinely measured routing cost-savings benchmark, and the concurrency stress test).

The two benchmarks in `tests/performance/test_cache_benchmark.py` are the platform's answer to the prompt's "include benchmarks where appropriate" requirement: they measure real `time.perf_counter()` timings and real `token_cost_usd` calls, print the actual numbers, and assert against conservative thresholds rather than mocked/hardcoded values. A representative run: **3381x** speedup for an L1 cache hit vs. a simulated 2ms backend call, and **96.0%** cost reduction ($48.00 → $1.90 per 1000 requests) when routing a realistic complexity mix through the tier selector instead of naively sending every request to the top tier.

### Disclosed scope boundaries

Consistent with every prior AIOS platform's honest-gap posture:

- The cache platform's "redis", "disk", and "cdn" layers are labels on the same DB-backed `CacheEntryModel` store today, not real Redis/filesystem/CDN clients. The `get`/`set`/`invalidate` contract on `CacheService` is exactly what a real per-layer backend would need to implement, so wiring one in is a swap-in behind the same interface, not a redesign — the in-process `LRUTTLCache` (L1) is real and would sit in front of any of them unchanged.
- Infra cost rates (`gpu_cost_per_hour_usd`, `cpu_cost_per_core_hour_usd`, etc.) and model-tier token pricing in `Settings` are illustrative, deployment-configurable defaults, not pulled live from a cloud billing API or a model provider's current price sheet. `pricing_rules.py` is deliberately rate-agnostic — every function takes the rate from `Settings`, so pointing this at real negotiated rates is a config change, not a code change.
- `GpuPoolService` models pool inventory, utilization reporting, and underutilization detection — it does not itself schedule inference batches onto GPUs, apply quantization/mixed-precision, or talk to a real cluster scheduler (Kubernetes device plugins, Slurm, etc.). It's the accounting and policy layer a real scheduler integration would report into.
- The auto-optimization engine's recommendations are generated from signals this platform itself already records (its own cache stats, latency samples, routing decisions, budget utilization) — it does not currently ingest signals from the other 20 AIOS platforms' own metrics. Cross-platform signal ingestion (e.g. reading `observability_platform`'s traces or `analytics_platform`'s KPIs directly) is a natural extension, not a currently-shipped capability.
- `RecommendationService.apply()` transitions a recommendation's status to `applied` — it does not itself execute the underlying change (raise a cache TTL, add a database index, downgrade a model tier). Applying a recommendation is currently a human/operator action this platform tracks the decision for, not one it automates end-to-end.

### Self-review

**Can this platform scale to millions of users?** The architecture is stateless per request (every service is built fresh off a per-request `RepositoryRegistry`/session) and the one piece of in-process state — the L1 `LRUTTLCache` — is bounded (`memory_cache_max_entries`) and safe to run per-replica without coordination, since the DB-backed L2 layer is the shared source of truth across replicas. What would matter most at real millions-of-users scale is the L2 layer's actual backend (see disclosed boundaries): a real Redis cluster instead of a relational table would be the next investment, and the interface is already shaped for that swap.

**Can infrastructure costs be reduced significantly?** Concretely and measurably, yes, for the two mechanisms this platform directly controls: the routing benchmark shows a 96% cost reduction from complexity-aware model selection on a realistic workload mix, and the cache benchmark shows a 3381x latency reduction (which translates directly to compute-time cost reduction for whatever expensive operation sits behind the cache). The GPU underutilization query and budget-near-exhaustion recommendations point at further infra savings but stop short of executing them automatically (disclosed above).

**Can response latency be improved across the stack?** This platform's own contribution is the cache layer (measured) and the latency/SLO tracking to detect regressions elsewhere (P95/P99 against configurable SLOs, feeding the auto-optimization engine's high-latency recommendation). The N+1 fixes applied directly to 8 call sites across 5 other platforms in Part 1 are a second, concrete latency improvement delivered in this phase, independent of this new platform.

**Can AI costs be optimized automatically?** Partially, and honestly disclosed as partial: routing is automatic and measurably effective; budget alerting is automatic; but turning a "systematic model-tier over-provisioning" recommendation into an actual policy change is still a human-in-the-loop `apply()` action today, not a closed automatic loop.

**Can the architecture support future hardware generations?** GPU pool types are a `Settings`-driven list (shared/dedicated/spot/reserved), not hardcoded branches, so a new hardware tier or pool type is a settings-list and enum-value change. The pricing/routing rules are similarly rate- and tier-agnostic pure functions over configuration, not hardcoded to today's model lineup.

**Can this compete with the performance characteristics of leading enterprise AI platforms?** The foundation — a real (not simulated) sub-microsecond L1 cache, a deterministic cost-aware router with measured 96% savings on a realistic mix, budget enforcement with real-time alerting, and an auto-optimization engine that mines its own signals — is there and proven with real numbers, not just passing tests. The gap that would matter most for a genuine "world-class" claim is the same shape as the disclosed boundaries above: this platform is the optimization and cost-intelligence *layer*; wiring its cache interface to a real Redis/CDN backend and its GPU pool accounting to a real cluster scheduler are the next investments, both already architected as swap-in points rather than redesigns.

### Running it

```bash
pip install -r requirements.txt
uvicorn perf_platform.perf_api.application_factory:create_app --factory --reload
```

Every request needs an `X-Tenant-Id` header; `X-User-Id` is optional (system-triggered actions like scheduled benchmark sweeps legitimately have no human actor). Interactive docs at `/docs`. Run `pytest tests/performance/test_cache_benchmark.py -s` to see the real measured cache-speedup and routing-cost-savings numbers printed.
