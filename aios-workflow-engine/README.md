# AIOS Enterprise Workflow Orchestration Engine

The execution backbone of the AI Operating System: a production-grade backend that orchestrates AI agents, prompt execution, memory operations, tool calls, human approvals, background jobs, scheduled tasks, external APIs, long-running processes, and event-driven automation, all as versioned, auditable workflow graphs.

This is Prior prompts delivered the AI Core (model execution), Prompt Platform, Agent Platform, and Memory Platform — this platform is the layer that actually runs multi-step processes across all of them, on a schedule or in response to events, with humans able to step in when a process calls for a decision.

## What it does

A workflow is a versioned, directed graph of typed nodes. A workspace owner builds a graph out of 30 node types (start/end, agent, prompt, memory read/write, retriever, knowledge search, decision, condition, loop, parallel branch, merge, delay, wait, approval, notification, webhook, REST API, database query, Python execution, file upload/processing, document parser, embedding generator, LLM call, function call, error handler, retry, and custom), across 16 workflow categories (AI agent, research, document processing, prompt pipeline, approval, data processing, ETL, knowledge pipeline, model inference, automation, notification, API integration, scheduled job, batch processing, streaming pipeline, event-driven).

Once published, a workflow version is immutable — editing always creates or updates a new draft, so an execution already in flight keeps running against the exact graph it started with, even if someone edits and republishes the workflow underneath it. The Execution Engine walks that graph node by node (sequential, parallel fan-out/merge, conditional and case-based branching, loops, nested/recursive sub-workflow invocation), tracking a full state machine per execution and per node, checkpointing after every node so a crashed or stalled run can be recovered without replaying work that already succeeded. Node failures retry with backoff up to a configured limit; if an execution still ends up FAILED, a saga-style rollback walks its successful nodes in reverse and compensates the ones marked compensable.

Human decisions are first-class: an APPROVAL node pauses the run, creates a real approval request with a multi-step chain of approvers, and only resumes execution once every step is resolved — with reassignment, escalation, expiry, comments, and a full audit trail along the way. A Task Scheduler fires workflows immediately, after a delay, at a calendar time, on a recurring interval, or on a cron expression, respecting per-schedule concurrency caps, rate limits, and schedule-to-schedule dependencies. An Event Bus underneath all of this publishes to internal handlers and webhook subscribers, with retryable delivery for the webhooks that fail.

## Architecture

```
workflow_platform/
  domain/            entities + state machines (Workflow, Execution, NodeExecution, ApprovalRequest, Schedule)
  models/             SQLAlchemy ORM models (13 tables across workflow, execution, approval, schedule, event, variable, governance, observability)
  repositories/        one repository per aggregate + a RepositoryRegistry unit of work
  workflow_core/       workflow CRUD, versioned graph editing, node/edge validation
  node_library/        the 30-node-type registry (NodeTypeSpec) + DB seeding
  workflow_engine/      the execution engine, node handlers, safe expression evaluator
  events/               event bus (pub/sub, webhooks) + subscription management
  scheduler/            schedule CRUD + the dispatcher that fires due schedules
  approval/             human-in-the-loop decision service
  state/                scoped variables (with secret encryption) + execution state/context
  recovery/             checkpoint restore + stalled-execution recovery sweep
  ai_bridges/           Protocol interfaces + in-process reference bridges to Agent/Prompt/Memory/Knowledge platforms
  monitoring/           execution timeline/graph, logs, success rate, latency, node duration, failure/retry stats, token usage
  security/             RBAC, audit log, workspace/org isolation, execution & approval policy enforcement
  workflow_api/         FastAPI routers (99 endpoints across 9 domains) + application factory
```

A few of the directories the original project brief called for by name — `analytics/`, `queue/`, `execution/`, `workflow_registry/`, `schemas/`, `templates/`, `variables/` — exist only as empty placeholders from initial scaffolding. Their intended functionality landed inside better-fitting modules instead: analytics inside `monitoring/` (the brief explicitly scoped a separate Analytics module out of this layer), queueing inside `events/` and `scheduler/`, node type registration inside `node_library/`, and scoped variables inside `state/`. Noting this here rather than leaving it to be discovered.

### Design decisions worth knowing about

**Versioned graphs, not versioned workflows.** `WorkflowModel` is stable identity; `WorkflowVersionModel` is an immutable graph snapshot once published. Executions pin to a `workflow_version_id`, not to "whatever the workflow currently looks like."

**One AsyncSession, one lock, per execution.** `ExecutionEngine` wraps every repository/session touch in a single `asyncio.Lock`, because SQLAlchemy's AsyncSession isn't safe for concurrent coroutine access. Node handler `execute()` calls — the actual I/O — run outside that lock, so PARALLEL_BRANCH nodes get genuine wall-clock concurrency. Each execution gets its own session (this is what a real request does too, via `workflow_api/dependencies.py`), so many concurrent executions run against independent locks, not one global bottleneck.

**Node definitions are optional, not required.** The 30-entry node type registry drives default timeout/retry/backoff/compensability, but every lookup degrades gracefully (300s timeout, 0 retries, not compensable) if a definition happens to be missing, rather than hard-failing a run.

**Secrets are opt-in only.** A variable marked `is_secret=True` is Fernet-encrypted at rest and excluded from any scope-chain resolution or template merge unless a caller explicitly asks for it — so a checkpoint, log line, or context-variable dump can't accidentally leak an API key.

**Observability reports only what's genuinely measured.** Token usage comes from real LLM call output; durations come from real timestamps. It does not fabricate CPU/memory/dollar-cost figures it has no real signal for — that gap is documented rather than papered over with invented numbers.

## REST API

99 endpoints across 9 routers, all under `/api/v1`: workspaces, workflows (CRUD + lifecycle), versions (draft/graph editing/publish) + the node type registry, executions (start/pause/resume/cancel/rollback/retry-node) + node execution history, schedules (all 5 schedule types + dispatcher tick), approvals (decide/reassign/escalate/expire/comment), events (publish + webhook/handler subscriptions), state (variables + execution state/checkpoints + recovery), observability (timeline/graph/logs/metrics), and governance (RBAC grants + audit log queries). Caller identity travels via an `X-User-Id` header (the same seam the Prompt and Agent Platforms use), on the assumption this sits behind an already-authenticated gateway.

## Testing

217 tests, all passing, across unit (domain state machines), repository-backed service tests for every module above, a dedicated `tests/api/` suite that drives the platform purely through HTTP end to end, and a `tests/performance/` suite covering: 20 fully independent concurrent executions racing against the same SQLite file, an 8-way parallel branch fan-out with a wall-clock timing assertion proving genuine concurrency (not serialized work wearing a "parallel" label), a 30-schedule dispatcher throughput check, a 30-execution stalled-recovery sweep, and 10 concurrent approval decisions each resolving its own paused execution. Every bug fixed along the way (state-machine transition edge cases, a timezone-naive/aware datetime subtraction bug from SQLite round-trips, a stricter tool bridge that correctly stopped silently echoing unregistered function calls, and others) was caught by a failing test, not by manual review.

Run the suite:
```
python3 -m pytest -q
```

## Self-review

**Can it scale horizontally?** Yes for the execution and API tiers — every FastAPI request gets its own session and its own `ExecutionEngine` instance, so N processes behind a load balancer each handle their own executions independently, coordinated only through the database. The one caveat: `SchedulerDispatcher`'s rate limiting is an in-memory sliding window scoped to a single dispatcher instance. Concurrency limits are already safe across multiple dispatcher processes (they read real execution counts from the database); rate limits would need a shared store (Redis, or a DB-backed counter) to be correct with more than one dispatcher running the tick loop. That's isolated to one method (`_check_rate_limit`) and documented in `scheduler/dispatcher.py`'s own module docstring.

**Does it recover gracefully from failure?** A crashed or stalled execution isn't lost: every node dispatch writes a checkpoint, `RecoveryService.recover_stalled_executions` sweeps executions stuck RUNNING past a configurable threshold and pauses them for a clean resume, and `restore_from_checkpoint` can roll an execution back to any prior checkpoint's exact context and position. Node-level failures retry with backoff before giving up; a run that still ends FAILED can be rolled back through saga-style compensation of its already-succeeded, compensable nodes. The stress suite specifically tests recovery at volume (30 stalled executions in one sweep), not just the 1-2-row correctness case.

**Can new node types be added without touching the core engine?** Yes — a node type is a `NodeTypeSpec` entry (key, default config/timeout/retry policy) plus a `NodeHandler` subclass registered in `HandlerRegistry`. The engine dispatches by looking up `node.node_type` in that registry; it has no type-specific branching of its own. Adding node type 31 means adding a spec and a handler, not editing `engine.py`.

**Can users build custom workflows without engine changes?** Yes — the graph (nodes, edges, conditions, config) is entirely data, built through the versioning API (`add_node`/`add_edge`/`replace_graph`) or a future visual builder on top of it. Branching logic itself is data too: CONDITION/DECISION nodes evaluate expressions through an AST-walking safe evaluator (no `eval()`), so a workflow author writes an expression string, not code the engine has to be changed to support.

**Is it trustworthy for mission-critical enterprise use?** RBAC is enforced with most-specific-grant-wins (a workflow-level grant beats a workspace-level one for that workflow), every RBAC change and approval decision writes to a consolidated, queryable audit log, secrets are encrypted at rest and excluded from context/log/checkpoint dumps by default, and workspace/organization isolation is asserted rather than assumed. What it does not yet have: real authentication (it trusts an `X-User-Id` header from whatever authenticates callers upstream) and a distributed rate limiter for multi-dispatcher deployments — both called out explicitly above rather than left implicit.

**Can it absorb future AI capabilities without a redesign?** The AI integration surface is a set of Protocol interfaces (`ai_bridges/interfaces.py`) — agent, prompt, memory, knowledge, document intelligence, tool — with in-process reference implementations that already call the real AI Core for LLM calls and embeddings. Swapping a reference bridge for a call into the real Agent Platform, Prompt Platform, or Memory Platform (once those services are reachable over the network) is a one-file change per bridge; the engine and its node handlers only ever depend on the Protocol, never the concrete implementation. Evaluation and MLOps integration were explicitly out of scope and would slot in the same way, as a new bridge, when their turn comes.

## What's explicitly out of scope (by design)

No Enterprise Evaluation Platform, no MLOps, no standalone Analytics module (observability covers metrics instead), and no frontend — this is the backend orchestration engine only.
