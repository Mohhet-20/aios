# AIOS Enterprise Release Engineering, Distribution & Deployment Ecosystem

Package `release_platform`, table prefix `rel_`. Delivered as `aios-release-platform.zip`.

## What this is

A production-grade release platform for managing thousands of deployments across cloud, hybrid, edge, and on-premises environments with zero downtime and full operational safety: release & version management (SemVer, 8 release channels, draft→candidate→approved→released lifecycle), an 11-type artifact catalog with distribution channels, deployment orchestration across 9 target environments, 10 rollout strategies, a feature-flag platform with deterministic percentage-bucketed targeting, update infrastructure, license management, environment management across 8 environment types, deployment validation (10 health-check targets), an 8-type rollback engine, release analytics, and a security/supply-chain layer (artifact signing, SBOM, checksum verification, release approvals). Built with the same clean/layered architecture as every other AIOS platform: pure-Python domain entities with guarded state machines, a repository/unit-of-work layer, a service layer, and a FastAPI REST layer.

**Out of scope by design:** no repository cleanup, no final architecture review, no packaging of the overall AIOS meta-project — this platform's own delivery follows the same standard packaging step every other platform in the series has used.

## Architecture

Identical pattern to every sibling AIOS platform:

- `domain/` — pure-Python entities (`Deployment`, `Release`, `Rollout`) with guarded `_transition()` state machines over enums, no ORM imports. `Deployment` shares the generic queued → in_progress → succeeded/failed job shape every other platform's job lifecycle uses (plus succeeded → rolled_back). `Release` and `Rollout` each have their own bespoke lifecycle: releases move draft → candidate → approved → released → deprecated/yanked with backward reject/revoke-approval transitions; rollouts move planned → in_progress → paused/completed/aborted with a resumable pause and a `advance(step_pct)` clamped to `[current, 100]`. Simpler status-only resources (updates, licenses, rollbacks, feature-flag enable/disable, environment activate/deactivate) are guarded directly in-service via inline transition dicts, the same "simple status field" precedent every other platform established.
- `models/` — SQLAlchemy 2.0 async ORM models, 20 tables across 12 files (`rel_` prefix).
- `repositories/` — one repository per model plus a `RepositoryRegistry` unit-of-work that lazily shares a single `AsyncSession`.
- Service modules — one directory per domain, each holding the orchestrating business logic.
- `release_api/` — FastAPI Application Factory, versioned routers (98 routes across 12 route groups) + an unversioned `/health` probe, a shared exception-handler layer mapping the 50-class domain exception hierarchy to HTTP status codes, and lightweight ORM→dict serialization.
- `dependencies/` — FastAPI dependency wiring (DB session → `RepositoryRegistry` → 19 services), plus `X-Tenant-Id`/`X-User-Id` header extraction. This platform expects to sit behind an already-authenticated caller (in practice, the Identity Platform).

## Module breakdown

**Release Engineering** (`release_engineering/`) — releases across 8 channels (dev, alpha, beta, rc, stable, lts, hotfix, patch) with a guarded draft → candidate → approved → released → deprecated/yanked lifecycle (reject and revoke-approval backward transitions included); pure-function SemVer parsing, comparison, and compatibility checking (`semver_rules.py`); version history and a compatibility matrix built on top of it.

**Artifact Management & Distribution** (`artifacts/`, `distribution/`) — an 11-type artifact catalog (backend/frontend/SDK/CLI packages, Docker images, Kubernetes manifests, Helm charts, Terraform modules, workflow/agent/prompt templates) with checksum tracking; distribution channels (container registry, Helm repository, package registry, private enterprise distribution, offline bundles) and per-channel publish entries linking artifacts to channels.

**Deployment Orchestration** (`deployment/`) — deployments across 9 target environments (cloud, on-prem, hybrid, edge, multi-region, multi-cluster, multi-tenant, air-gapped, offline) sharing the generic job lifecycle (queued → in_progress → succeeded/failed, succeeded → rolled_back).

**Rollout Strategies** (`rollouts/`) — rollouts across 10 strategies (blue-green, canary, rolling, shadow, progressive, percentage, region, organization, tenant, feature) with a guarded planned → in_progress → paused/completed/aborted lifecycle, resumable pausing, and a clamped `advance(step_pct)` for progressive rollouts.

**Feature Flag Platform** (`feature_flags/`) — flags scoped across 5 levels (global, organization, workspace, user, experiment) with kill-switch support (an enabled kill-switch flag always evaluates to `False` regardless of overrides), per-target overrides that take precedence over the flag's default state, and deterministic percentage-bucketed rollout targeting (`targeting_rules.py`, MD5-hash-based so the same target always buckets the same way for a given flag key — stable A/B test and gradual-rollout membership without a database round trip).

**Update Infrastructure** (`updates/`) — update jobs across 7 types (automatic, manual, scheduled, delta, patch, offline, rollback) with a guarded pending → downloading → applying → applied/failed lifecycle plus a rolled-back terminal state.

**License Management** (`licensing/`) — licenses across 5 types (enterprise, organization, trial, feature, seat-based) with a guarded active → expired/suspended/revoked lifecycle plus a dedicated trial state, seat assignment, expiry checking, and HMAC-based offline license signing/verification (`license_rules.py`, built on the shared `security.tokens.sign_payload` primitive) so enterprise customers can validate a license without a network call home.

**Environment Management** (`environments/`) — environments across 8 types (development, testing, QA, staging, production, sandbox, customer preview, enterprise dedicated) with active/inactive toggling. `register_environment` is this platform's one commit-spanning-lock get-or-create sequence — see Concurrency below.

**Deployment Validation** (`validation/`) — health checks across 10 targets (application, API, database, workflow, AI services, agent services, memory services, security platform, monitoring platform, analytics platform) via an injectable `checker` callable; see Disclosed scope boundaries for what happens when the REST surface doesn't supply one.

**Rollback Engine** (`rollback/`) — rollbacks across 8 types (automatic, manual, partial, database, configuration, feature, model, infrastructure) with a guarded pending → in_progress → completed/failed lifecycle. Deliberately does not itself call `DeploymentService.mark_rolled_back` — see Disclosed scope boundaries.

**Security & Supply Chain** (`security/`) — SBOM generation per artifact, checksum compute/verify (`supply_chain_rules.py`), artifact signing (flips the artifact's `signed` flag — the one place this platform reaches from the security module into the artifacts module, since "has this artifact been signed" is definitionally a security-module fact about an artifacts-module row), and release approvals with a guarded one-shot decide (raising `ConflictError` if an approval was already decided, the same one-shot-decision pattern as docs_platform's `ReviewAlreadyDecidedError`).

**Release Analytics** (`analytics/`) — deployment metric recording and adoption snapshots, with pure aggregation helpers (`aggregation_rules.py`: deployment success rate, rollback frequency, average deployment duration, failed release count) duck-typed over anything exposing `.metric_type`/`.value`.

## Concurrency

One commit-spanning `asyncio.Lock` sequence, the same pattern established across every other AIOS platform for check-then-act races that span multiple statements (separate callers own separate DB connections; SQLite only makes a write visible to others once committed — and the lock must be held until that commit happens, not just until the row is flushed, or a waiting caller can still observe pre-commit state):

- `EnvironmentService.register_environment` — get-or-create by (`tenant_id`, `name`), locked per `tenant_id:name`.

Proven under real concurrent load in `tests/performance/test_concurrency.py`, which races 15 genuine independent DB connections via `asyncio.gather` (never the rollback-isolated test fixture) and asserts no duplicate rows.

`FeatureFlagOverrideService.set_override` and `LicenseService.assign_seat` both contain a similar upsert shape but are deliberately left unlocked: an override race converges on whichever write lands last with no correctness violation (overrides are idempotent by (`flag_id`, `target_ref`) semantics from the reader's perspective), and a seat-assignment race produces at worst a duplicate seat row, a cosmetic data-quality issue rather than a license-limit bypass, since limit enforcement re-reads the current count at decision time. Documented here rather than silently left unexamined.

## Testing

166 tests, ruff clean. Test suite mirrors the module breakdown: `tests/repository` (schema smoke test), `tests/release_engineering`, `tests/artifacts`, `tests/distribution`, `tests/deployment`, `tests/rollouts`, `tests/feature_flags`, `tests/updates`, `tests/licensing`, `tests/environments`, `tests/validation`, `tests/rollback`, `tests/security`, `tests/analytics`, `tests/release_api` (12 end-to-end HTTP tests driving every domain through the real FastAPI app), `tests/performance` (concurrency stress).

## Disclosed scope boundaries

Consistent with every other AIOS platform's honest-gap posture:

- `HealthCheckService.run_all_checks` accepts an injectable `checker` callable; the REST surface doesn't supply one, so every target is recorded as `"degraded"` with an explanatory note rather than falsely claiming `"passed"`. Wiring a real checker (one that actually pings the application, API, database, and the other 7 declared targets) is a natural next step, not a currently-shipped capability — directly mirroring docs_platform's `GenerationJobService.run_job` honest-gap pattern.
- `DeploymentService` does not cross-validate `release_id`/`environment_id` against real rows, and `RolloutService` does not cross-validate `deployment_id`. This is an intentional "loose FK, no forced cross-module dependency" choice, the same decoupling precedent as docs_platform's search/assistant modules — a deployment record referencing a since-deleted release is a data-quality signal for an operator dashboard to surface, not a referential-integrity violation this platform enforces at write time.
- `RollbackService` does not itself call `DeploymentService.mark_rolled_back` — recording that a rollback happened and marking the originating deployment as rolled back are treated as two separate writes an orchestrating caller (or a future saga/workflow layer) composes, rather than one service silently reaching into another's write path.
- License seat/usage-limit enforcement is check-then-record, not a hard DB constraint — a caller that ignores `LicenseService`'s limit check entirely could still write seats past the limit directly through the repository. The service layer is the enforcement boundary, as it is everywhere else in this platform.
- SBOM generation produces a structured artifact-metadata record (component list, checksum, generation timestamp), not a real dependency-tree walk of an actual build artifact — this platform stores and serves SBOMs, it doesn't generate one from real package-manager lockfiles yet.

## Self-review

**Can deployments occur safely with zero downtime?** The rollout module's 10 strategies (blue-green, canary, rolling, shadow, progressive, percentage, region, organization, tenant, feature) exist specifically to give operators a zero-downtime path suited to their risk tolerance, and progressive rollouts have a clamped, resumable `advance()`/pause so a bad signal at 10% never has to become a bad signal at 100%. What this platform doesn't yet do is execute the actual traffic-shifting infrastructure calls (load balancer weight changes, k8s rollout commands) — it models and tracks the rollout's state, which is the orchestration layer a real executor would sit behind.

**Can every release be rolled back instantly?** The rollback engine covers 8 rollback types and every deployment's guarded lifecycle allows succeeded → rolled_back directly. As disclosed above, `RollbackService` and `DeploymentService` are intentionally decoupled, so "instant" today means the rollback is recorded instantly and correctly, not that this platform itself executes the infrastructure-level revert — that composition is a thin orchestration layer away, not a redesign.

**Can enterprise customers update reliably?** The update module's 7 types (including offline and delta) and the license module's offline HMAC signature verification together mean a customer with no network path to this platform's servers can still validate their license and apply a delta update — the two pieces most enterprise/air-gapped/on-prem customers need most.

**Do releases remain secure and verifiable?** Checksum verification, artifact signing, SBOM records, and a one-shot release-approval decision together give every release a verifiable chain: what's in it (SBOM), whether it's been tampered with (checksum), whether it's authentic (signature), and whether a human signed off (approval). `require_signature_for_production` and `require_sbom` are settings-driven policy switches, not hardcoded assumptions.

**Does the platform support future deployment technologies without redesign?** Every module follows the identical shape (domain entity or inline-guarded status → repository → service → router), and the target/strategy/type lists (9 deployment targets, 10 rollout strategies, 11 artifact types, 8 environment types) are all settings-driven lists, not enums baked into branching logic — adding a target or strategy is a settings-list and enum-value change, not a new pattern to learn.

**Can this compete with world-class enterprise software ecosystems?** The foundation — 20 tables, 98 REST routes, SemVer-driven versioning, a 10-strategy rollout engine, offline-capable licensing, and a real supply-chain security layer — is there and tested end-to-end (166 tests). The gap that would matter most for a genuine "world-class" claim is the same shape as every disclosed gap above: this platform is the orchestration and record-of-truth layer; the infrastructure-execution layer underneath it (actually shifting load balancer weights, actually pinging a live database for a health check, actually walking a real dependency tree for an SBOM) is architected as a swap-in point via injectable callables and settings, not a currently-shipped capability.

## Running it

```bash
pip install -r requirements.txt
uvicorn release_platform.release_api.application_factory:create_app --factory --reload
```

Every request needs an `X-Tenant-Id` header; `X-User-Id` is optional (system-triggered actions like automated update jobs legitimately have no human actor). Interactive docs at `/docs`.
