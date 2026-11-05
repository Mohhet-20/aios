# AIOS Enterprise API Gateway, Integration Hub & Service Mesh Platform

Package `gateway_platform`, table prefix `gw_`. Delivered as `aios-api-gateway-platform.zip`.

## What this is

The communication backbone of the AI Operating System: an API gateway with a route registry and OAuth-ready API management (keys, rate limiting, quotas, versioning, JWT, schema validation), a service mesh (discovery, load balancing, circuit breakers, health checks with automatic recovery), traffic management across ten routing strategies, an event platform (topics, subscriptions, publish/deliver/retry/replay with dead-lettering), an integration hub with a 16-type connector catalog, a webhook platform with HMAC-signed delivery, protocol translation across three protocol pairs plus API-version and auth transformation, gateway security (policies, IP/geo filtering, request signing, threat detection, security events), observability/analytics/topology, and a developer experience layer (OpenAPI spec, sample generation, SDK code generation, a testing console, webhook testing). Built with the same clean/layered architecture as every other AIOS platform: pure-Python domain entities with guarded state machines, a repository/unit-of-work layer, service layer, and a FastAPI REST layer.

**Out of scope by design:** no Enterprise Analytics Platform, no Testing Platform, no Documentation Platform.

## Architecture

Identical pattern to every sibling AIOS platform:

- `domain/` — pure-Python entities (`ApiRoute`, `ApiKey`, `ApiVersion`, `CircuitBreaker`, `EventMessage`, `WebhookDelivery`, `IntegrationConnection`, `SdkGenJob`) with guarded `_transition()` state machines over enums, no ORM imports. Simpler status-only resources (service registrations/instances, traffic rules, event topics/subscriptions, connectors, webhook subscriptions, OAuth clients, security policies, protocol translation configs) are guarded directly in-service instead, the same precedent set by every other platform's own "simple status field" resources.
- `models/` — SQLAlchemy 2.0 async ORM models, 30 tables across 11 files (`gw_` prefix).
- `repositories/` — one repository per model plus a `RepositoryRegistry` unit-of-work that lazily shares a single `AsyncSession`.
- Service modules — one directory per domain, each holding the orchestrating business logic.
- `gw_api/` — FastAPI Application Factory, versioned routers (119 routes across 12 route groups) + an unversioned `/health` probe, a shared exception-handler layer mapping the 68-class domain exception hierarchy to HTTP status codes, and lightweight ORM→dict serialization.
- `dependencies/` — FastAPI dependency wiring (DB session → `RepositoryRegistry` → services), plus `X-Tenant-Id`/`X-User-Id` header extraction. This platform expects to sit behind an already-authenticated caller (in practice, the Identity Platform).

## Module breakdown

**API Gateway core** (`gateway_core/`) — the route registry every inbound request is matched against, one row per (path, method, protocol), with a guarded draft → active ↔ deprecated → retired lifecycle and support for six visibility tiers (internal, external, public, private, partner, admin) and six protocols (REST, GraphQL, WebSocket, SSE, streaming, gRPC-ready).

**API Management** (`api_management/`) — `gwk_`-prefixed API key issuance (raw key returned once, only a hash and 12-character prefix persisted), a DB-backed sliding-window rate limiter plus a separate daily quota check, versioned API lifecycle (active → deprecated with a settings-driven sunset notice → retired), HS256 JWT issuance/validation, OAuth-ready client registration (secret hashed at rest), and a deliberately scoped JSON-Schema-subset request/response validator (type/required/properties/items/enum only).

**Service Mesh** (`service_mesh/`) — service discovery/registry with instance-level health state, load balancing (weighted, random, round-robin, and a disclosed round-robin-fallback approximation of least-connections), circuit breakers (closed → open → half-open, auto-recovering after a configurable cooldown), and health checks with automatic recovery (one healthy result recovers an instance; N consecutive unhealthy results degrade it).

**Traffic Management** (`traffic/`) — one generic rule table covering all ten routing strategies the prompt specifies (weighted, split, canary, blue-green, header, path, region, priority, mirror, failover), each with its own free-form config shape, resolved in descending priority order.

**Event Platform** (`events/`) — topics categorized across the workflow/agent/prompt/security/system/custom taxonomy, filtered subscriptions, and a publish → attempt-delivery → deliver/fail/retry/dead-letter lifecycle with a replay window, mirroring the Webhook Platform's delivery shape via an injectable deliverer.

**Integration Hub** (`integrations/`) — a connector catalog spanning the 16 enterprise systems the prompt specifies (CRM, ERP, email, calendar, cloud storage, GitHub, GitLab, Jira, Confluence, Slack, Microsoft Teams, Salesforce, SAP, and custom REST/GraphQL/enterprise), plus per-tenant integration connections guarded through pending → connected/error → connected/disconnected. This is a connector catalog and connection lifecycle, not a live third-party API client.

**Webhook Platform** (`webhooks/`) — subscription management with an opaque `vault://webhook-secrets/...` secret reference minted once per subscription, event-type matching, HMAC-signed delivery attempts with configurable retry/backoff into dead-lettering, and full delivery replay.

**Protocol Translation** (`protocols/`) — a config registry plus real, stateless transformer functions for all three declared pairs (REST↔GraphQL, REST↔WebSocket, REST↔Event Stream), plus standalone API-version schema translation (field rename/removal) and authentication-header transformation (bearer↔API-key).

**Gateway Security** (`gateway_security/`) — a generic policy table across the six policy types the prompt specifies (IP filter, geo restriction, rate limit, request signing, bot detection, threat detection), real CIDR-based IP filtering and country-code geo filtering (both with a configurable default-allow/default-deny fallback), HMAC request-signature verification, lightweight bot/threat detection heuristics (known-bot user-agent markers, request-rate thresholds, SQL-injection/XSS signature scanning), and an append-only security events feed.

**Observability, Analytics & Topology** (`observability/`) — raw time-series metric recording across the nine metric types the prompt specifies plus real aggregation helpers (average, total, error rate), a live dependency-graph topology service with running-average latency per service edge, and periodic analytics snapshots across the eight report types the prompt specifies.

**Developer Experience** (`devx/`) — a real OpenAPI 3.0.3 spec builder driven by the platform's own route registry (API Explorer/Swagger backing), sample request/response generation from a registered JSON schema, SDK code generation (a real `ast`-validated Python HTTP client and a structurally-sanity-checked TypeScript client) through a guarded queued → running → completed/failed job lifecycle, an API testing console that records every "try it out" request/response, and a webhook dry-run testing service.

## Concurrency

Three commit-spanning `asyncio.Lock` sequences, the same pattern established across every other AIOS platform for check-then-act races that span multiple statements (separate callers own separate DB connections; SQLite only makes a write visible to others once committed — and the lock must be held until that commit happens, not just until the row is flushed, or a waiting caller can still observe pre-commit state):

- `ConnectorService.register_connector` — get-or-create by connector type, locked per `tenant_id:connector_type`.
- `ServiceRegistryService.register_service` — get-or-create by service name, locked per `tenant_id:name`.
- `EventTopicService.register_topic` — get-or-create by topic name, locked per `tenant_id:name`.

All three are proven under real concurrent load in `tests/performance/test_concurrency.py`, which races genuine independent DB connections via `asyncio.gather` (never the rollback-isolated test fixture) and asserts no duplicate rows and no lost writes.

## Testing

194 tests, ruff clean. Test suite mirrors the module breakdown: `tests/repository` (schema smoke test), `tests/gateway_core`, `tests/api_management`, `tests/service_mesh`, `tests/traffic`, `tests/events`, `tests/integrations`, `tests/webhooks`, `tests/protocols`, `tests/gateway_security`, `tests/observability`, `tests/devx`, `tests/gw_api` (12 end-to-end HTTP tests driving every domain through the real FastAPI app), `tests/performance` (concurrency stress).

## Disclosed scope boundaries

Consistent with every other AIOS platform's honest-gap posture:

- The connector catalog (`ConnectorService`) is a config catalog, not a live third-party API client — actually calling out to Slack/GitHub/Salesforce/etc. is out of scope for this control plane, the same disclosed boundary the Developer Platform's MCP integration module drew.
- `least_connections` load-balancing is a disclosed approximation falling back to round-robin, since this control plane doesn't do real-time per-instance connection accounting.
- JWT service does issuance and validation only, not a full OAuth2 authorization-code/token-exchange flow; OAuth client service does registration and secret verification only, not a full authorization server.
- `SchemaValidationService` validates a deliberately scoped JSON-Schema subset (type/required/properties/items/enum) — no `$ref`, `oneOf`/`anyOf`/`allOf`, `pattern`, or `format`.
- Protocol translation transforms payload/schema/auth shape via field-mapping and envelope conventions — it does not implement the GraphQL, WebSocket, or event-stream wire protocols themselves.
- Threat/bot detection is heuristic (known-bot user-agent substrings, request-rate thresholds, a small injection-signature list) — not a full WAF or ML-based classifier.
- Code generation output is genuinely validated for Python (`ast.parse()` on every generated file) but only structurally sanity-checked for TypeScript, since validating TS syntax properly needs a TypeScript compiler this platform doesn't ship.
- API keys, OAuth client secrets, and webhook signing secrets are never persisted in the clear — only a hash (keys/clients) or an opaque `vault://...` pointer (webhook secrets) is stored. Raw values are returned to the caller exactly once, at issuance/rotation or subscription creation.

## Running it

```bash
pip install -r requirements.txt
uvicorn gateway_platform.gw_api.application_factory:create_app --factory --reload
```

Every request needs an `X-Tenant-Id` header; `X-User-Id` is optional (system-triggered checks legitimately have no human actor). Interactive docs at `/docs`.
