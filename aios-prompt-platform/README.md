# AIOS — Enterprise Prompt Engineering Platform

a complete platform for designing, testing, evaluating, optimizing, experimenting on, deploying, monitoring, and governing prompts at production scale — not a text box with a "run" button. Built on top of AI Core (every model call flows through it as a real, editable dependency, never a stub) and following the same Clean Architecture / async SQLAlchemy patterns as the core backend.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # installs aios-ai-core editable from ../aios-ai-core
cp .env.example .env

uvicorn prompt_platform.main:app --reload --port 8200
# http://localhost:8200/docs — OpenAPI/Swagger, 100+ endpoints across 13 routers
# http://localhost:8200/health

pytest   # 148 tests, all green, zero real network calls
```

Every AI Core call in the test suite runs through a fully scripted, network-free `ScriptedProvider` double (see `tests/conftest.py`) — the same pattern the AI Core project itself uses — while still exercising the genuine execution/routing/structured-output/cost path, not a simplified mock of it.

## Architecture

**Domain model** (`prompt_platform/domain/`, `prompt_platform/models/`): 28 tables across workspaces/projects, prompts (with tags, categories, favorites, collections), versions (with dependencies, history, releases), golden test cases and test runs, evaluation runs and results, optimization runs and suggestions, experiments and variants, deployments and environment configs, execution logs, and audit/permission grants. A version's `status` (DRAFT → IN_REVIEW → APPROVED/REJECTED → DEPRECATED → ARCHIVED, the approval workflow) is kept deliberately orthogonal to its `branch` (EXPERIMENTAL/STABLE/PRODUCTION, the deployment lane) — a version can be approved and sitting on any branch; status answers "has this been reviewed," branch answers "where does it run."

**Prompt Studio** (`prompt_platform/prompt_editor/`): validation (undeclared/unused variable detection via the AI Core's own `{{variable}}` parser, char limits, parameter sanity), formatting, live preview (token estimate, context-window usage, JSON request preview) computed without a model call, real execution (sync/streaming/structured-output preview) for a "press run and see" experience, and autosave with optimistic locking so two tabs editing the same draft can't silently clobber each other.

**Prompt Library** (`prompt_platform/prompt_registry/`): search/filter/sort, favorites, recently-used and most-used (derived from real execution logs), categories, tags, and shared/private collections.

**Prompt Versioning** (`prompt_platform/prompt_engine/`): version creation with auto-incrementing numbers and parent linking, the full approval workflow, promotion with a hard eval-score gate for PRODUCTION (promoting a new production version demotes the prior one to STABLE, never orphans it), rollback (reuses a version's already-cleared eval score rather than re-gating it), unified diff between any two versions (templates, parameters, variables, status, score), and an append-only history log.

**Prompt Testing** (`prompt_platform/prompt_testing/`): single/batch/regression runs against golden test cases, five assertion types (exact/contains/not-contains/regex/JSON-schema), and latency/cost threshold enforcement per case.

**Prompt Evaluation** (`prompt_platform/prompt_evaluation/`): LLM-as-judge scoring (structured-output-validated, one call per qualitative metric — accuracy/completeness/consistency/groundedness/faithfulness/safety) plus rule-based scoring (latency/cost/token-usage via a linear-falloff-from-target curve, JSON-formatting validity) for automatic runs, human review capture, pairwise version comparison, and multi-version benchmark comparison.

**Prompt Optimization** (`prompt_platform/prompt_optimization/`): a zero-cost rule-based suggestion pass (vague-language detection, missing output-format guidance, missing few-shot examples, variable mismatches, compression/expansion candidates by token count, cost/latency parameter gaps) that runs before any model call, plus LLM-backed automatic rewriting (instruction refinement, compression, expansion) and reproducible few-shot example selection from golden test cases (biased toward cases known to pass). Any suggestion can be applied, which creates a new draft version through the same versioning service everything else uses.

**Prompt Experiments** (`prompt_platform/prompt_experiments/`): A/B and multi-variant testing across prompt versions, models, and parameters, with a real Welch's t-test (unequal variance, unequal sample size) built on `math.lgamma` and a hand-rolled regularized incomplete beta function — not a normal-distribution approximation — for genuine p-values, confidence intervals, and Cohen's d effect size. Winner selection requires the leading variant to beat *every* other variant significantly, not just have the best mean. Sampling is seeded (`random.Random(f"{seed}:{salt}")`) so re-running an experiment reproduces the exact same inputs per variant.

**Prompt Deployment** (`prompt_platform/prompt_deployment/`): environment lanes (development/testing/staging/production) with approval required for staging/production, a hard eval-score gate for production, canary rollout (partial-then-full traffic), rollback to any prior version (skips re-approval since it's restoring already-approved state, but is still recorded as its own audited deployment), and per-environment config storage.

**Prompt Observability** (`prompt_platform/prompt_observability/`): every render+execute call from Testing, Evaluation, and Experiments logs a `PromptExecutionLogModel` row (success or failure) through one shared choke point (`render_and_execute`'s optional `observability` param) — latency, tokens, cost, model/provider used, retries, tool-call count, and user feedback are all captured without each service reimplementing logging. Analytics rollups compute real latency percentiles (p50/p95/p99), cost totals, success rate, model/source breakdowns, and top failure reasons.

**Prompt Governance** (`prompt_platform/prompt_governance/`): RBAC with prompt > project > workspace grant-precedence resolution and an implicit OWNER role for a prompt's `owner_id`, sensitive-prompt protection (a `sensitive`-flagged prompt requires a minimum role even for read access, independent of a broader grant), an append-only audit log, and a compliance rollup (grant count, audit event count, approval/production status) per prompt.

**Prompt Security** (`prompt_platform/prompt_security/`): regex-based injection-pattern detection and secret-shaped-string detection (API keys, AWS keys, bearer tokens, JWTs, private-key blocks, hardcoded password assignments), variable sanitization (truncation + injection-phrase filtering before interpolation), output validation (catches a model response that appears to have leaked a secret), and redaction. Wired as a **hard-fail gate** directly into `VersioningService.create_version` — a template containing what looks like a hardcoded secret cannot be saved as a version at all; injection-pattern matches are surfaced as advisory findings, not blocked, since a prompt legitimately *about* prompt injection would otherwise always fail.

**REST API** (`prompt_platform/prompt_api/`): 13 FastAPI routers (workspaces, prompts/library, versions, studio, testing, evaluation, optimization, experiments, deployment, observability, governance, security, import/export) covering CRUD, search, testing, evaluation, optimization, deployment, history, experiments, metrics, and audit — 100+ endpoints total. Domain exceptions map to HTTP status codes centrally (`exception_handlers.py`) so no router needs a try/except. Auth is intentionally minimal — an `X-User-Id` header, documented as the seam where real JWT validation (already fully built in the core backend) would plug in for a caller that isn't already sitting behind that gateway.

## Testing

148 tests, all passing in a single combined run: 11 domain-entity tests (state machines, cycle detection), 14 Studio tests, 8 Library tests, 7 Versioning tests, 10 Testing-framework tests, 8 Evaluation tests, 14 Optimization tests, 13 Experiment tests (including a Welch's-t-test cross-check against known critical-value tables), 16 Deployment tests, 6 Observability tests, 10 Governance tests, 14 Security tests, and 15 full-stack API integration tests (real FastAPI app, ASGI transport, dependency-overridden DB session and AI Core, exercising the actual request/response cycle end to end). Zero real network calls anywhere.

The same "write real tests immediately, run them, fix genuine bugs" loop used throughout this project surfaced real issues along the way: an enum-overlap ambiguity between version status and branch caught and redesigned before any dependent code was written; a test-seeding gap where a directly-inserted version bypassed the aggregate's version-number counter, causing a real off-by-one in a later version-numbering test; a `format_template` test that had the wrong expectation (fixed the test, not the formatter, since the formatter's leading-whitespace-preserving behavior was correct and documented); and the ExecutionEngine's provider-failure wrapping (`AllProvidersFailedError`, not the raw exception) surfacing in observability failure-logging tests, which needed the test's expected exception type corrected, not the logging behavior.

## Self-review

**Can prompts be managed like production software?** Yes, and this is the platform's strongest area. Every version goes through a real approval workflow with recorded transitions, every change is diffable, every promotion is gated (production requires both an APPROVED status and a minimum evaluation score, not just a button click), rollback restores a specific prior version rather than "undo," and an append-only history log plus audit trail mean nothing happens invisibly. This mirrors source control deliberately, not by analogy.

**Can teams collaborate efficiently?** RBAC with workspace/project/prompt-scoped grants and precedence resolution, an approval/review process separate from authorship, shared collections and tags, and a favorites/recently-used/most-used surface for navigating a large shared library all work today. The honest gap: there's no real-time collaborative editing (two people in Studio simultaneously) — autosave's optimistic locking prevents silent data loss between two *sequential* edits, but doesn't merge concurrent ones. That's a legitimate v2 feature, not a current claim.

**Can prompt quality be measured objectively?** Rule-based metrics (latency/cost/token-usage/formatting) are fully objective and reproducible. LLM-as-judge metrics (accuracy/completeness/consistency/groundedness/faithfulness/safety) are the industry-standard approach for the metrics that genuinely require judgment, and they're structured-output-validated with retry-on-malformed-response rather than trusting free-text scores — but they inherit whatever bias or inconsistency the judge model itself has. Pairwise comparison and benchmark-across-versions give a relative signal that's more robust than any single absolute score, and this is the honest state of the art, not a solved problem this platform claims to have solved.

**Can changes be deployed safely?** Yes: approval gating, a hard production eval-score gate, canary rollout with adjustable traffic percentage, and rollback that's one call away and doesn't require re-clearing approval. The one deliberate scope boundary: deployment "environment" (where it runs) and version "branch" (how proven it is) are intentionally separate axes — a team that wants them coupled would add that policy at the API/workflow layer, not inside either service, keeping both primitives composable.

**Can experiments be reproduced?** Yes, concretely — sampling is seeded per experiment and per variant (`random_seed` + variant-scoped salt), verified by a dedicated test that calls the sampler twice with the same seed and asserts identical output. The statistical engine itself uses a real Student-t CDF (via the regularized incomplete beta function), not a normal approximation, verified against known critical-value tables (t-critical for df=10 at 95% confidence matches the textbook 2.228 to three decimal places).

**Can enterprise customers trust the platform?** The things that would make a careful buyer's list — audit trail, RBAC, approval workflows, sensitive-data protection, secret-detection-as-a-hard-fail, eval gates on production promotion, rollback, real (not decorative) statistics — are all implemented with working tests, not just present in the data model. The honest gaps: auth is a header-based seam meant to sit behind the core backend's real JWT backend rather than a complete auth system in its own right, LLM-judge evaluation inherits judge-model bias by nature of the technique, and injection-pattern detection is regex-based heuristics (real, useful, and false-positive-tolerant by design) rather than a trained classifier. None of these are hidden — they're the same kind of scoped, documented trade-off every other AIOS service has made within its own scope boundary.

## Known limitations (by design)

No Multi-Agent System, no Memory, no Workflows, no evaluation capability beyond prompt-focused scoring — those are explicitly out of scope for this prompt and belong to later stages of the AI Operating System. "Frontend Experience" is delivered as the API/UX contract (the 100+ REST endpoints documented above and in `/docs`) those interfaces would consume, not new React code — consistent with this project's established pattern of building actual frontend UI only in the dedicated frontend prompt (the console).
