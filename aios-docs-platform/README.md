# AIOS Enterprise Documentation, Knowledge Portal & Learning Platform

Phase 20 of the AIOS build. Package `docs_platform`, table prefix `doc_`. Delivered as `aios-docs-platform.zip`.

## What this is

The official source of truth for the entire AI Operating System: a documentation core spanning 15 doc types (architecture, backend, frontend, api, sdk, workflow, agent, prompt, knowledge, infrastructure, deployment, security, developer, admin, enterprise_customer), API/SDK documentation across REST/GraphQL/WebSocket/streaming and 10 SDK targets with an automated generation-job engine, an architecture portal (diagrams + technology stack), a knowledge base across 9 article types, a role-based learning platform (tutorials, learning paths, enrollment/progress tracking), a retrieval-based AI documentation assistant, an enterprise search platform, versioning & release notes, collaboration (comments, reviews, audit trail), documentation analytics, and RBAC-backed security & governance. Built with the same clean/layered architecture as every prior AIOS platform: pure-Python domain entities with guarded state machines, a repository/unit-of-work layer, a service layer, and a FastAPI REST layer.

**Out of scope by design:** release packaging and a hosted demo environment.

## Architecture

Identical pattern to every sibling AIOS platform:

- `domain/` — pure-Python entities (`GenerationJob`, `DocPage`) with guarded `_transition()` state machines over enums, no ORM imports. `GenerationJob` shares the generic queued → running → completed/failed shape every prior platform's job lifecycle uses; `DocPage` has its own bespoke editorial lifecycle (draft → in_review → published → archived/deprecated) since editorial semantics don't map onto generic start/complete/fail. Simpler status-only resources (KB articles, enrollments, reviews) are guarded directly in-service instead, the same "simple status field" precedent every prior platform established.
- `models/` — SQLAlchemy 2.0 async ORM models, 23 tables across 11 files (`doc_` prefix).
- `repositories/` — one repository per model plus a `RepositoryRegistry` unit-of-work that lazily shares a single `AsyncSession`.
- Service modules — one directory per domain, each holding the orchestrating business logic.
- `doc_api/` — FastAPI Application Factory, versioned routers (91 routes across 11 route groups) + an unversioned `/health` probe, a shared exception-handler layer mapping the 48-class domain exception hierarchy to HTTP status codes, and lightweight ORM→dict serialization.
- `dependencies/` — FastAPI dependency wiring (DB session → `RepositoryRegistry` → services), plus `X-Tenant-Id`/`X-User-Id` header extraction. This platform expects to sit behind an already-authenticated caller (in practice, the Identity Platform).

## Module breakdown

**Documentation Core** (`documentation/`) — doc spaces (one per subsystem/team, keyed by `tenant_id:key`) and doc pages with a guarded draft → in_review → published → archived/deprecated lifecycle. Every `update_content` call on a draft page snapshots a new immutable version row, which is what the versioning module reads from.

**API / SDK Documentation & Automation** (`api_docs/`, `sdk_docs/`, `automation/`) — API doc entries across four protocol types (REST, GraphQL, WebSocket, streaming) with request/response/auth examples and error docs; SDK doc entries across all 10 declared SDK targets (Python, TypeScript, Java, Go, C#, CLI, Plugin SDK, Extension SDK, Webhook SDK, MCP SDK); a generation-job engine with a guarded queued → running → completed/failed lifecycle and an injectable `generator` callable — when none is supplied (the REST surface's default), it produces an honest `{"generated": False, "note": "no generator function supplied"}` result rather than pretending to have introspected a live codebase.

**Architecture Portal** (`architecture/`) — diagrams across the 7 declared types (system overview, sequence, component, deployment, infrastructure map, service map, dependency graph) with BFS-traversed related-diagram discovery over a bidirectional adjacency map (built from every diagram's one-directionally-authored `related_refs`, since "related to" is symmetric for the reader even though authored one-directionally), plus a technology stack registry.

**Knowledge Base** (`knowledge/`) — articles across the 9 declared types (how-to, best practice, troubleshooting, FAQ, release note, migration guide, design pattern, reference, glossary) with a draft → published → archived lifecycle and tag-based lookup.

**Learning Platform** (`learning/`) — tutorials across 4 types with per-tutorial pass thresholds, role-based learning paths (administrator, developer, enterprise_customer), and enrollment tracking against exactly one of a tutorial or a learning path, with a guarded enrolled → in_progress → completed/abandoned lifecycle that auto-advances on the first progress update and auto-completes once progress crosses the pass threshold.

**AI Documentation Assistant** (`assistant/`) — retrieval-and-extract question answering over the published-content pool (published pages + published KB articles only — draft/archived content is never surfaced), confidence-thresholded so low-overlap questions get no answer rather than a bad guess; related-doc suggestion, troubleshooting-article lookup, extractive summarization, outdated-page detection (published pages unreviewed past a settings-driven staleness window), and templated code-example generation. Explicitly **not** LLM-backed — see Disclosed scope boundaries.

**Search Platform** (`search/`) — keyword/full-text search over the same published-content pool via overlap-scoring, with every query logged for popularity and failed-search analytics, an optional doc-type filter, and click-through recording. Deliberately does not import the assistant module despite the shared ranking approach — each is a legitimate standalone entry point for a different UI.

**Versioning & Release Notes** (`versioning/`) — read-side access to the immutable content snapshots the documentation core writes, a unified-diff between any two versions of a page, release notes across 5 kinds grouped by version label, and deprecation notices with an optional planned-removal date.

**Collaboration** (`collaboration/`) — page/target comments with a resolve flag, review requests with a guarded pending → approved/changes_requested/rejected decision (raising a dedicated `ReviewAlreadyDecidedError` rather than a generic transition error if decided twice), and an append-only audit log that any domain service can write to.

**Analytics** (`analytics/`) — raw event recording across 5 event types (page view, search query, tutorial started/completed, feedback submitted) with pure aggregation helpers (most-viewed pages, failed-search rate, tutorial completion rate, content freshness scoring via linear decay over a settings-driven window), feedback scores (1-5, averaged per subject), and broken-link tracking with a resolved flag.

**Security & Governance** (`security/`) — RBAC role assignments across 5 hierarchical roles (viewer < contributor < editor < owner < admin), each optionally scoped to a doc space/page with tenant-wide fallback; visibility enforcement (internal pages require at least a viewer role assignment, public pages are open to anyone including anonymous callers); and an explicit `GovernanceService.assert_editable()` guard raising `VersionProtectedError` for published/archived/deprecated pages, complementing `DocPageService.update_content`'s own inline draft-only check.

## Concurrency

One commit-spanning `asyncio.Lock` sequence, the same pattern established across every prior AIOS platform for check-then-act races that span multiple statements (separate callers own separate DB connections; SQLite only makes a write visible to others once committed — and the lock must be held until that commit happens, not just until the row is flushed, or a waiting caller can still observe pre-commit state):

- `DocSpaceService.register_space` — get-or-create by (`tenant_id`, `key`), locked per `tenant_id:key`.

Proven under real concurrent load in `tests/performance/test_concurrency.py`, which races 15 genuine independent DB connections via `asyncio.gather` (never the rollback-isolated test fixture) and asserts no duplicate rows.

`RoleAssignmentService.assign_role` and `EnrollmentService.enroll` both contain a similar get-or-create/upsert shape but are deliberately left unlocked: a role re-assignment race produces at worst a duplicate row with no ordering guarantee (a cosmetic data-quality issue, not a correctness violation, since `get_role` just needs any matching row), and an enrollment race is idempotent by design once retried. Documented here rather than silently left unexamined.

## Testing

141 tests, ruff clean. Test suite mirrors the module breakdown: `tests/repository` (schema smoke test), `tests/documentation`, `tests/api_docs` / `tests/sdk_docs` / `tests/automation`, `tests/architecture`, `tests/knowledge`, `tests/learning`, `tests/assistant`, `tests/search`, `tests/versioning`, `tests/collaboration`, `tests/analytics`, `tests/security`, `tests/doc_api` (12 end-to-end HTTP tests driving every domain through the real FastAPI app), `tests/performance` (concurrency stress).

## Disclosed scope boundaries

Consistent with every prior AIOS platform's honest-gap posture:

- The AI Documentation Assistant is a retrieval-and-extract system (keyword-overlap scoring + extractive summarization), not LLM-backed. `AssistantService` is documented as a drop-in replacement point for a future real LLM call — the confidence-thresholding and candidate-pool-restriction logic around it would stay the same either way.
- `GenerationJobService.run_job` does not itself introspect a live codebase, database schema, or dependency graph — it orchestrates the job lifecycle and calls an injectable `generator` callable. The REST surface doesn't supply one, so `POST /generation-jobs/{id}/run` always produces the honest `{"generated": False, ...}` result. Wiring a real generator (e.g., one that walks the actual `docs_platform` package and models) is a natural next step, not a currently-shipped capability.
- `AssistantService.generate_code_example` is a templated stub keyed by SDK language, not real code generation from a live API surface.
- `DiagramModel.content` is a free-form DSL/text blob, not a validated diagram spec (Mermaid, PlantUML, etc.) — this platform stores and relates diagrams, it doesn't render or validate diagram syntax.
- Search and the AI assistant both implement near-identical keyword-ranking logic and intentionally don't share an implementation — each is a legitimate standalone entry point for a different UI (search console vs. assistant chat), and the shared logic is small enough that a cross-module dependency isn't worth the coupling.
- Documentation freshness/staleness detection is review-date-based (`last_reviewed_at` vs. a settings-driven window), not code-diff-based — this platform doesn't currently cross-reference doc pages against the actual source files they describe to detect drift.

## Self-review

**Can a new engineer become productive quickly?** The module breakdown above maps 1:1 onto the folder structure, and every service file carries a docstring explaining its one job and any non-obvious decision behind it (the two-transition-graph domain design, the bidirectional-adjacency fix for diagram traversal, why search and the assistant don't share code). An engineer reading `documentation/doc_page_service.py` learns the page lifecycle without needing to read anything else first.

**Can enterprise customers deploy successfully using only the documentation?** The API/SDK documentation module and the generation-job engine exist specifically to keep deployment-relevant docs (config, schema, dependency, architecture reports) generated from the platform itself rather than hand-written and prone to drift — though as disclosed above, the generator callable itself isn't wired to a real introspector yet, so today this is scaffolding for that workflow rather than the finished workflow.

**Can architecture remain understandable as the platform grows?** Every module follows the identical shape (domain entity or inline-guarded status → repository → service → router), so adding a 16th doc type or an 11th SDK target is a settings-list change plus a new enum value, not a new pattern to learn.

**Can documentation stay synchronized with code automatically?** Partially, and honestly disclosed as partial: the generation-job lifecycle and the outdated-page detector (`AssistantService.detect_outdated_pages`) give the scaffolding for staying in sync, but neither currently diffs against real source. This is the platform's most significant gap relative to "world-class," and the natural next investment.

**Can the AI assistant answer documentation questions accurately?** Within its disclosed scope, yes: it only ever answers from published content, refuses to answer below a confidence threshold rather than guessing, and is directly testable (13 tests cover confident/low-confidence/no-match paths). It cannot answer questions requiring reasoning beyond keyword overlap — a real LLM backend would close that gap without needing to change the surrounding service's contract.

**Can this become one of the world's best enterprise documentation platforms?** The foundation — 23 tables, 91 REST routes, RBAC-scoped visibility, versioned content with diffing, collaboration workflow, and analytics — is there and tested end-to-end. The two gaps that would matter most for a genuine "world's best" claim are a real LLM behind the assistant and a real code/schema introspector behind the generation-job engine; both are architected as swap-in points rather than dead ends.

## Running it

```bash
pip install -r requirements.txt
uvicorn docs_platform.doc_api.application_factory:create_app --factory --reload
```

Every request needs an `X-Tenant-Id` header; `X-User-Id` is optional (system-triggered actions like automated generation jobs legitimately have no human actor). Interactive docs at `/docs`.
