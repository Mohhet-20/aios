# AIOS Enterprise Developer Platform & SDK Ecosystem

Package `developer_platform`, table prefix `dev_`. Delivered as `aios-developer-platform.zip`.

## What this is

The developer-facing surface of the AI Operating System: API key issuance and rate limiting, a versioned OpenAPI-compatible API layer, a real Python reference SDK, a Click-based CLI, a plugin SDK with a guarded manifest → signed → published lifecycle, an extension point framework, a webhook platform with HMAC-signed delivery and retry, an MCP (Model Context Protocol) integration control plane, an OpenAPI-driven code generation engine, a developer portal with ephemeral sandboxes, a generic multi-type package registry, developer usage analytics, and developer-facing security (RBAC, opaque secret references, plugin isolation policy, OAuth scope negotiation). Built with the same clean/layered architecture as every other AIOS platform: pure-Python domain entities with guarded state machines, a repository/unit-of-work layer, service layer, and a FastAPI REST layer.

**Out of scope by design:** no Enterprise Analytics, no Final Documentation, no Release Candidate.

## Architecture

Identical pattern to every sibling AIOS platform:

- `domain/` — pure-Python entities (`PluginVersion`, `ApiKey`, `WebhookDelivery`, `McpServer`, `CodeGenJob`, `SandboxEnvironment`, `PortalContent`, `RegistryPackageVersion`) with guarded `_transition()` state machines over enums, no ORM imports. Simpler status-only resources (CLI sessions, extension registrations, MCP servers/sessions, portal content) are guarded directly in-service instead, the same precedent set by the Infrastructure Platform.
- `models/` — SQLAlchemy 2.0 async ORM models, 28 tables across 10 files (`dev_` prefix).
- `repositories/` — one repository per model plus a `RepositoryRegistry` unit-of-work that lazily shares a single `AsyncSession`.
- Service modules — one directory per domain, each holding the orchestrating business logic.
- `dev_api/` — FastAPI Application Factory, 12 versioned routers (97 endpoints) + an unversioned `/health` probe, a shared exception-handler layer mapping the 54-class domain exception hierarchy to HTTP status codes, and lightweight ORM→dict serialization.
- `dependencies/` — FastAPI dependency wiring (DB session → `RepositoryRegistry` → services), plus `X-Tenant-Id`/`X-User-Id` header extraction. This platform expects to sit behind an already-authenticated gateway (in practice, the Identity Platform).
- `sdks/python/` — a standalone, installable reference SDK (`aios-dev-sdk`) with its own `pyproject.toml`: sync and async HTTP clients, tenacity-backed retry with rate-limit backoff honoring `Retry-After`, pagination and streaming helpers, typed error hierarchy.
- `cli/` — a standalone, installable Click CLI (`aios-cli`) with its own `pyproject.toml`, built on top of `aios-dev-sdk`: `aios auth`, `aios config`, per-resource `list`/`create` command groups, `aios deploy`, `aios logs` (streaming), `aios monitor`, `aios diagnostics`, `aios update`.

## Module breakdown

**API Platform** (`api_platform/`) — API key issuance (`dpk_`-prefixed raw key returned once at issuance/rotation, only a hash and a 12-character prefix persisted), DB-backed sliding-window rate limiting, versioned API lifecycle (active → deprecated with a settings-driven sunset notice period → sunset), and a real OpenAPI 3.0.3 spec builder used by both the docs endpoint and the code generation engine.

**SDK Platform** (`sdk_platform/`) — a version compatibility matrix (SDK major version × supported API version range, per language) plus a package registry entry point reusing the generic registry tables. Backs the actual `sdks/python/aios_dev_sdk` reference implementation shipped alongside this platform.

**CLI Platform** (`cli_platform/`) — short-lived CLI session tokens (hashed at rest exactly like an API key, default 30-day TTL) and a command execution audit log. Backs the actual `cli/aios_cli` CLI shipped alongside this platform.

**Plugin SDK** (`plugin_sdk/`) — plugin registration, a guarded version lifecycle (draft → validated → signed → published, deprecate reachable from published), structural manifest validation (required fields, permission allowlist, category), real HMAC-SHA256 signing over the canonical manifest, checksum-based packaging, dependency chain resolution with cycle and depth limits, and a marketplace submit → approve/reject → install/rate flow.

**Extension Framework** (`extension_framework/`) — an extension point registry across 11 categories (agent, prompt, workflow, memory, tool, model, evaluation, dashboard, authentication, notification, UI component) with a guarded registration lifecycle (registered → active ↔ disabled).

**Webhook Platform** (`webhook_platform/`) — subscription management with a real opaque secret reference minted per subscription, event-type matching (including wildcard patterns), HMAC-signed delivery attempts with configurable retry/backoff, and full delivery replay. The signing secret is never persisted in the clear and is returned to the caller only once, at subscription creation.

**MCP Integration** (`mcp_integration/`) — a control plane for Model Context Protocol servers: server registration and connection lifecycle, session management with permission checks, and capability discovery/sync (resources, tools, prompts) via a pluggable transport adapter. This is a control plane, not a live wire-protocol implementation — `StaticTransportAdapter` is the reference adapter for declared or test capabilities; a real stdio/HTTP/SSE transport plugs into the same `McpTransportAdapter` seam.

**Code Generation Engine** (`codegen/`) — generates a real, `ast`-validated Python HTTP client (models + client class) and a structurally-sanity-checked TypeScript client from an OpenAPI-shaped spec, through a guarded job lifecycle (queued → running → completed/failed) that persists every generated file as a checksummed artifact.

**Developer Portal & Sandbox** (`developer_portal/`) — versioned content pages (getting-started, docs, tutorials, quickstarts, release notes, migration guides) with a guarded draft → published ↔ archived lifecycle and an edit-increments-version counter, plus ephemeral sandbox environments with a per-developer concurrency cap and expiration sweep.

**Package Registry** (`registry_platform/`) — a generic catalog spanning all five package types this platform distributes (SDK, plugin, workflow template, prompt template, agent template) through one `dev_registry_packages` / `dev_registry_package_versions` table pair, with dependency graph resolution (cycle detection, latest-published-version resolution) and deprecation-notice scheduling.

**Developer Analytics** (`developer_analytics/`) — sampled usage-event recording (8 typed event kinds, sample rate configurable per tenant) and activity dashboards (usage summary, top resources, most active developers) built with `collections.Counter` over a bounded recent-events window.

**Developer Security** (`dev_security/`) — a lightweight 3-tier RBAC (viewer < operator < admin) with optional per-scope bindings falling back to a tenant-wide grant, opaque secret references (`vault://...` pointers — this platform never persists a raw secret value), plugin isolation policy evaluation (allow/deny-list permission checking, not runtime sandboxing — that concern already lives in the Tool Platform), and OAuth scope negotiation (validate/narrow, not a full OAuth2 provider).

## Concurrency

Three commit-spanning `asyncio.Lock` sequences, the same pattern established across every other AIOS platform for check-then-act races that span multiple statements (separate callers own separate DB connections; SQLite only makes a write visible to others once committed — and the lock must be held until that commit happens, not just until the row is flushed, or a waiting caller can still observe pre-commit state):

- `PluginLifecycleService.register_plugin` — get-or-create by plugin name, locked per `tenant_id:name`.
- `PackageRegistryService.register_package` / `.publish_version` — get-or-create by package identity and check-then-insert by version, locked per `tenant_id:name:package_type` and `tenant_id:package_id:version` respectively.
- `DeveloperRbacService.grant_role` — upsert by principal/scope, locked per `tenant_id:principal_id:scope`.

All three are proven under real concurrent load in `tests/performance/test_concurrency.py`, which races genuine independent DB connections via `asyncio.gather` (never the rollback-isolated test fixture) and asserts no duplicate rows and no lost writes. Each lock's critical section commits before releasing — an earlier draft released the lock before commit, which a stress test caught immediately (two concurrent registrations both observed "no existing row" and both inserted).

## Testing

216 tests total, 95% coverage on the core platform, ruff clean. Test suite mirrors the module breakdown: `tests/repository` (schema smoke test), `tests/api_platform`, `tests/sdk_platform`, `tests/cli_platform`, `tests/plugin_sdk`, `tests/extension_framework`, `tests/webhook_platform`, `tests/mcp_integration`, `tests/codegen`, `tests/developer_portal`, `tests/registry_platform`, `tests/developer_analytics`, `tests/dev_security`, `tests/dev_api` (14 end-to-end HTTP tests driving every domain through the real FastAPI app), `tests/performance` (concurrency stress) — 186 tests. Plus two standalone sibling packages, each with their own suite testing entirely through mocked HTTP transport with zero live-server dependency: `sdks/python/tests` (12 tests) and `cli/tests` (18 tests).

## Disclosed scope boundaries

Consistent with every other AIOS platform's honest-gap posture:

- MCP Integration is a control plane that tracks servers/sessions/capabilities — it does not itself speak the stdio/HTTP/SSE wire protocol. `McpTransportAdapter` is the seam a real transport implementation plugs into.
- Plugin isolation is policy *evaluation* (allow/deny-list permission checking against a declared manifest), not runtime sandbox enforcement — actual process/network isolation for a running plugin is out of scope for this control plane.
- OAuth scope negotiation validates and narrows requested scopes against granted scopes; it is not a full OAuth2 authorization server.
- Code generation output is genuinely validated for Python (`ast.parse()` on every generated file) but only structurally sanity-checked for TypeScript, since validating TS syntax properly needs a TypeScript compiler this platform doesn't ship.
- API keys, CLI session tokens, and webhook signing secrets are never persisted in the clear — only a hash (keys/sessions) or an opaque `vault://...` pointer (webhook secrets, developer security secret references) is stored. Raw values are returned to the caller exactly once, at issuance or rotation.

## Running it

```bash
pip install -r requirements.txt
uvicorn developer_platform.dev_api.application_factory:create_app --factory --reload
```

Every request needs an `X-Tenant-Id` header; `X-User-Id` is optional (system-triggered checks legitimately have no human actor). Interactive docs at `/docs`.

To use the reference SDK and CLI standalone:

```bash
pip install -e sdks/python
pip install -e cli
aios auth login --api-key <your-key> --base-url http://localhost:8000
aios project list
```
