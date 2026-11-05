# AIOS — Enterprise Backend Platform

a production-grade FastAPI backend implementing Clean Architecture for the Enterprise AI Operating System designed in the original architecture and served by the frontend in the console. This is the central orchestration layer — auth, organizations/teams/workspaces, 22 business services, background jobs, events, observability — with AI model logic deliberately stubbed behind a real interface, by design.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # edit SECRET_KEY etc. for real deployments
uvicorn app.main:app --reload --port 8000
# http://localhost:8000/docs  — OpenAPI/Swagger
# http://localhost:8000/health/live, /health/ready, /metrics

pytest                        # 35 tests, all green
```

Default `DATABASE_URL` is `sqlite+aiosqlite:///./aios.db` for zero-setup local dev. Point it at `postgresql+asyncpg://...` for anything beyond a laptop — nothing in the codebase above `app/database/session.py` knows or cares which engine is behind `DATABASE_URL`.

## Architecture

Clean Architecture, dependency pointing inward:

- **`app/domain/`** — pure Python entities and business rules, zero framework/ORM imports. Flagship aggregates (`Prompt`/`PromptVersion`, `WorkflowExecution`, `Agent`, `User`/`Organization`, `EvaluationRun`) enforce real invariants here: a `PromptVersion` cannot promote to production below a 90.0 eval score; promoting a new production version demotes the old one; a `WorkflowExecution` can only move through its state machine in valid transitions; an `Agent` checks its own tool permissions.
- **`app/models/`** — SQLAlchemy ORM (28 tables), separate from domain entities. Services map between the two for flagship aggregates; simpler CRUD-shaped entities skip the mapping and let `BaseCRUDService`/`SQLAlchemyRepository` work on the ORM model directly. That's an explicit simplification, not an oversight — see Self-Review.
- **`app/repositories/`** + **`app/database/unit_of_work.py`** — generic repository per entity, wired through a `UnitOfWork` for transactional multi-repository operations. Optimistic locking is manual (compare-and-increment a `version` column), not SQLAlchemy's `version_id_col`, because that mapper argument doesn't compose with the mixin-based model hierarchy used here.
- **`app/application/` + `app/services/`** — 22 named business services (Project, Workspace, Agent, Prompt, Model, Workflow, Inference, Evaluation, Memory, Knowledge, Embedding, Vector, Dataset, Experiment, Document, Conversation, Search, Monitoring, Notification, Configuration, Plugin, Audit), each behind a `Protocol` interface in `app/application/interfaces/services.py`.
- **`app/api/` + `app/routers/v1/`** — ~26 versioned routers, 86 registered routes, mounted under `/api/v1`. Health and metrics mount unversioned at root since they're infra, not product API.
- **`app/security/`** — JWT access/refresh tokens, bcrypt password hashing, RBAC (`Permission`/`Role` enums, `ROLE_PERMISSIONS` mapping), API keys for service accounts, a `Principal` abstraction unifying both auth methods behind one `get_current_principal()` dependency.
- **`app/events/`** — in-process async pub/sub for domain events (UserRegistered, PromptPromoted, WorkflowExecutionCompleted, etc.), with default handlers wiring events to audit logs and notifications.
- **`app/workers/`** — asyncio-based background job queue (`InProcessWorkerPool`) with retry/backoff, backing long-running workflow execution, batch inference, evaluation runs, embedding generation, document processing, and notification jobs.
- **`app/infrastructure/`** — swappable adapters: `ai_providers/` (stubbed model provider, real integration is future work), `vector_store/` (in-memory cosine similarity, swappable to pgvector/Qdrant/Pinecone), `cache/` (in-memory, swappable to Redis).
- **`app/monitoring/`** — Prometheus metrics, liveness/readiness health checks. **`app/logging/`** — structlog with request/correlation ID propagation via contextvars.
- **`app/middleware/`** — request ID, access logging, sliding-window rate limiting, security headers, registered in that order in `app/core/application_factory.py` alongside CORS/GZip.

## Testing

35 tests across unit (domain logic, permissions), repository, API (auth flow incl. refresh rotation, prompt lifecycle incl. 403 on missing permission), integration (workflow execution through the background worker, evaluation run completion, semantic memory write/query), security (auth required on protected routes, rate limiting), and a performance smoke test. All pass in both chunked and full-suite runs.

One real bug class was found and fixed while writing these tests: SQLite's `DateTime(timezone=True)` doesn't round-trip `tzinfo` through `aiosqlite`, which broke naive/aware datetime comparisons in token-refresh and workflow-duration logic — fixed with `app/core/time_utils.ensure_aware_utc()`, applied at both call sites. A second, subtler bug — the file-based test database throwing `database is locked` only when the full test suite ran in one process — was fixed by enabling WAL mode, a 30s busy timeout, and `NullPool` for file-based SQLite in `app/database/session.py` (see inline comments there for why).

## Self-review (Principal Backend Engineer)

**Can this scale to millions of requests?** The layering supports it — services don't know whether they're backed by SQLite or Postgres, the event bus and task queue are behind abstract interfaces with a documented swap to Kafka/NATS/Redis Streams and Celery/RQ/Arq, and nothing in the request path assumes single-process state except the two dev-mode singletons (in-process event bus, in-process worker pool) that are explicitly called out as the pre-production upgrade path. What would NOT scale as-is: the in-memory vector store and in-memory cache are O(n) and single-process by construction — fine's scope, a hard blocker for real traffic. Swapping either requires implementing the existing `VectorStore`/`Cache` ABCs against a real backend, not restructuring callers.

**Can another engineer understand it quickly?** The directory names match their contents (domain means domain, no framework leakage; services are one file per business area; routers are one file per resource). The one place this breaks down slightly: not every entity has a rich domain object — a new engineer reading `app/domain/entities/` and expecting a `Workspace` or `Dataset` aggregate there won't find one, because those are simple enough to be served directly off the ORM model via `BaseCRUDService`. That asymmetry is documented inline and in this README, but it's a real "why is X here and Y not" question a new hire will ask once.

**Can new AI capabilities be added without major refactoring?** This is the part the whole platform is built around. `ModelProviderAdapter` (generate/stream/embed) is the single seam real model integration plugs into — `InferenceService`, `EmbeddingService`, and the streaming router endpoints already call through this interface and emit the right events/metrics; swapping `StubModelProvider` for an OpenAI/Anthropic/vLLM adapter touches one file and zero callers. Same story for `VectorStore` and `TaskQueue`. This was the central design bet of the core backend, and it holds up.

**Is the architecture modular? Is every service cohesive?** Yes on both, with one caveat: `PromptService` and `WorkflowService` are the two "flagship" services doing real domain-state-machine work and are noticeably heavier than the other 20, which are closer to typed CRUD wrappers. That's proportional to actual complexity (prompt promotion and workflow execution have real business rules; a notification doesn't), not an accident, but it means those two files are the ones to read first when auditing service quality.

**Would this pass a production architecture review?** For an internal platform or funded pre-launch product, yes, with the reviewer's follow-up questions being exactly the ones answered above: swap plan for the three dev-mode infra pieces (event bus, task queue, vector store/cache), and a real AI provider integration. Both are one-file swaps behind existing interfaces, not rewrites — which is the actual measure of whether this foundation was worth building this way.

## Known limitations (by design)

No real AI model logic — `StubModelProvider` returns clearly-labeled deterministic placeholder text/embeddings; wiring a real provider is explicitly future work. The event bus and task queue are in-process/single-instance (documented swap path to Kafka/NATS/Redis Streams and Celery/RQ/Arq). The vector store and cache are in-memory. Optimistic locking is manual rather than via SQLAlchemy's `version_id_col`. Alembic is scaffolded but has no populated migration scripts yet — `init_models()` creates tables directly for dev/test. SQLite is the zero-setup default; the `ensure_aware_utc` fix documents the one behavioral gap versus Postgres.
