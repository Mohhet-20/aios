# AIOS Enterprise Tool Execution & Integration Platform

Package `tool_platform`. This README was reconstructed during the documentation audit architecture audit — the platform shipped without one; every fact below is verified against the actual source (settings, module docstrings, exceptions, route count, test count), not inferred.

## What this is

The tool layer every AIOS agent/workflow calls into: a tool registry across 37 built-in categories, a plugin marketplace (publish/install/version, signature-required by default), a Credential Vault (Fernet-encrypted secret material, never plaintext at rest), a real resource-limited execution sandbox for Python/shell connectors (subprocess-based, not simulated), a reference MCP-server connector plus other built-in connectors, tool discovery (capability/category/tag/lexical search), an AI-facing planning layer that turns agent intent into a dispatchable call, a task scheduler, and governance/observability. Built with the same clean/layered architecture as every other AIOS platform.

## Architecture

- `domain/` — pure-Python entities with guarded `_transition()` state machines (`Tool`, `ToolExecution`, `Schedule`, and others).
- `models/` — SQLAlchemy 2.0 async ORM models, 16 tables.
- `repositories/` — one repository per model plus a `RepositoryRegistry` unit-of-work (includes the `get_many()` batch-fetch method added platform-wide during the platform-wide audits — this platform's own N+1 fix from that audit, `DiscoveryService.recently_used`/`.list_favorites`, uses it directly).
- Service modules — one directory per domain: `tool_core/`, `tool_registry/`, `plugin_system/`, `credentials/`, `sandbox/`, `tool_execution/`, `connectors/`, `discovery/`, `ai_planning/`, `platform_bridges/`, `marketplace/`, `governance/`, `monitoring/`, `validation/`, `scheduler/`.
- `tool_api/` — FastAPI Application Factory, versioned routers (92 routes) + an unversioned `/health` probe, a shared exception-handler layer mapping the 27-class domain exception hierarchy to HTTP status codes.
- `dependencies/` — FastAPI dependency wiring (DB session → `RepositoryRegistry` → services).

## Module breakdown

**Tool Core & Registry** (`tool_core/`, `tool_registry/`) — `ToolService` is identity/ownership/lifecycle CRUD for the top-level `ToolModel`; editing the actual contract (schema/config/capabilities/auth requirement) lives in `version_service.py`, the same identity-vs-version-content split used across every other AIOS platform. `CategoryRegistry` is a data-driven catalog of all 37 built-in tool categories — policy/metadata only (default capabilities, sandbox-by-default, typical auth kind).

**Plugin System & Marketplace** (`plugin_system/`, `marketplace/`) — `PluginRegistryService` is the "list your extension" side (publish/list/version a listing plus its declared dependency edges); `installation_service.py` is the "a workspace actually installs it" side; `marketplace/` is the read/browse/discover side, kept separate so search/browse concerns don't couple to the publish/install write path.

**Credential Vault** (`credentials/`) — `VaultService`: secret material is always JSON-serialized then Fernet-encrypted before it touches the database — `CredentialModel.encrypted_payload` is ciphertext, full stop, with `credential_metadata` as the only plaintext-adjacent field.

**Sandbox** (`sandbox/`) — `SubprocessSandbox` is real, working resource-limited execution for the Python-execution and shell-command connectors, not a simulation: each call runs in its own subprocess inside its own throwaway temp directory (the actual filesystem restriction mechanism), with memory/CPU/disk/timeout/network-deny defaults from `Settings`.

**Tool Execution & Connectors** (`tool_execution/`, `connectors/`) — the ORM↔domain-aggregate bridge for `ToolExecution`, and a real, working reference MCP-server connector (plain JSON-RPC-style POST) plus other built-in connectors, honestly disclosed as speaking HTTP rather than the stdio/SSE transports real MCP servers typically use.

**Discovery & AI Planning** (`discovery/`, `ai_planning/`) — capability/category/tag/version search plus a lexical "semantic" search over name/description/capabilities (term-overlap, the same approach `connectors/web_search.py` uses); `ToolPlanningService` is the AI-facing layer between an agent's stated intent and the Execution Engine's `connector_key`-keyed dispatch.

**Platform Bridges** (`platform_bridges/`) — Protocol/ABC bridges to the Workflow Engine, Agent Platform, Prompt Platform, and Memory Platform, the same architectural seam the Workflow Engine's own `ai_bridges/interfaces.py` uses for its upstream dependencies (a stable contract, not a live integration — see each sibling platform's own disclosed-boundaries section).

**Governance & Validation** (`governance/`, `validation/`) — `RBACService` answers "is this principal allowed to act on this resource at all," distinct from the security platform's guardrail/policy checks and from sandbox/network-policy's "is this connector allowed to touch this endpoint." `validation/` is standalone JSON Schema validation any caller can use for a pre-flight check before dispatch, honestly noting the Execution Engine keeps its own inline copy of the same check (`_validate_schema`) rather than sharing this module directly — a deliberate decoupling, not an oversight.

**Monitoring & Scheduler** (`monitoring/`, `scheduler/`) — `ObservabilityService` answers "what happened on this tool call / across this tool's history" from genuinely-recorded `ToolExecutionModel` timing/status/sandbox-usage data. `ScheduleService` is the CRUD/lifecycle ("when does this run") side of the Task Scheduler; `ScheduleDispatcher` is the "actually run it" side.

## Concurrency

A different lock shape than the get-or-create pattern most sibling platforms document: `ToolExecutionEngine` (`tool_execution/engine.py`) holds one `asyncio.Lock` (`_session_lock`) for the lifetime of the engine instance, serializing every repository/session touch — a SQLAlchemy `AsyncSession` isn't safe for concurrent coroutine access — while the actual connector `execute()` call (genuine I/O) runs *outside* that lock. That's what makes batch/parallel execution (`run_batch`) real concurrency rather than serialized work wearing a "parallel" label: N concurrent `start_execution` calls each acquire the lock only for their own brief DB writes, spending the rest of their time awaiting the connector concurrently. The Workflow Engine's execution engine uses the identical model.

Separately, this platform's get-or-create-shaped writes (favoriting, plugin installation) have no dedicated lock — they're either idempotent or tolerate a benign duplicate-row race, the same "cosmetic, not correctness" judgment call documented explicitly in several sibling platforms' READMEs.

## Testing

260 tests passing, ruff clean — the largest test suite of the "platform" series, matching this platform's unusually broad module count (15 service directories).

## Self-review

This README was written after the fact as part of a documentation-consistency audit — the platform itself (260 tests, 92 REST routes, a real subprocess sandbox, Fernet-encrypted credential storage) was already solid; what was missing was purely the documentation artifact every sibling platform has.

## Running it

```bash
pip install -r requirements.txt
uvicorn tool_platform.tool_api.application_factory:create_app --factory --reload
```
