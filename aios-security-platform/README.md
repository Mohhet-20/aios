# AIOS Enterprise Security, Guardrails & AI Governance Platform

Phase 14 of the AIOS build. Package `security_platform`, table prefix `sec_`. Delivered as `aios-security-platform.zip`.

## What this is

The security backbone for the AI Operating System: AI guardrails (prompt injection / jailbreak / unsafe-instruction detection, structured output validation, response filtering), data protection (PII detection/redaction, sensitive data classification, DLP), a policy engine with scope-based inheritance, secrets management with real envelope encryption, dynamic risk scoring, threat detection, AI governance (asset lifecycle + approval workflows), security events, an immutable audit log, and compliance tooling (frameworks, evidence, retention, legal holds, consent, data residency). Built with the same clean/layered architecture as every prior AIOS platform: pure-Python domain entities with guarded state machines, a repository/unit-of-work layer, service layer, and a FastAPI REST layer.

**Out of scope by design:** no Production Infrastructure & MLOps, no Performance Optimization, no Developer SDK.

## Architecture

Identical pattern to every sibling AIOS platform:

- `domain/` — pure-Python entities (`Policy`, `GuardrailViolation`, `Secret`, `ThreatDetection`, `ApprovalRequest`) with guarded `_transition()` state machines over enums, no ORM imports.
- `models/` — SQLAlchemy 2.0 async ORM models, 29 tables across 8 files (`sec_` prefix).
- `repositories/` — one repository per model plus a `RepositoryRegistry` unit-of-work that lazily shares a single `AsyncSession`.
- Service modules — one directory per domain, each holding the orchestrating business logic.
- `sec_api/` — FastAPI Application Factory, 12 versioned routers (89 endpoints) + an unversioned `/health` probe, a shared exception-handler layer mapping the ~40-class domain exception hierarchy to HTTP status codes, and lightweight ORM→dict serialization.
- `dependencies/` — FastAPI dependency wiring (DB session → `RepositoryRegistry` → services), plus `X-Tenant-Id`/`X-User-Id` header extraction. This platform expects to sit behind an already-authenticated gateway (in practice, the Identity Platform).

## Module breakdown

**Policy Engine** (`policies/`) — policy CRUD with version snapshots on every rules edit, time-boxed exceptions (capped at `max_policy_exception_days`), and scope-based evaluation with most-specific-wins inheritance across 10 policy scopes (organization → dataset).

**AI Guardrails** (`guardrails/`) — regex-pattern heuristic detectors for prompt injection, jailbreak, indirect prompt injection, and unsafe instructions; a deliberately-scoped JSON-Schema-subset structured output validator; regex-based response filtering/redaction. The orchestrating `GuardrailService` runs the right detector for the content's source, checks tenant-defined custom rule overrides, decides allow/flag/block, persists an append-only evaluation log plus violation records, and raises `GuardrailViolationError` on block. `GuardrailViolationService` covers the review lifecycle (open → acknowledged → resolved).

**Data Protection — PII & DLP** (`pii/`, `dlp/`) — regex-based PII detection (email, phone, SSN, credit card with Luhn checksum, IP address — honestly scoped; name/address/passport/bank-account/medical-record detection needs a trained NER model and isn't attempted here), redaction/masking (partial masking for card-like numbers), sensitive data classification, and DLP policy evaluation (allow/flag/redact/block) with automatic escalation to block on critical-severity findings. `DlpService.assemble_secure_context` filters and redacts content fragments before they reach an LLM context window — the security-filtering counterpart to the Memory Platform's context assembly engine.

**Secrets Management & Encryption** (`secrets/`, `encryption/`) — a credential vault with real AES-256-GCM envelope encryption (`encryption/envelope.py`), versioned secrets (every rotation mints a new encrypted version rather than overwriting), access policies with logged reads (granted or denied), and environment secret injection. Key material is never stored directly — `EncryptionKeyModel.material_ref` is an opaque reference from which the real key is derived via PBKDF2 over the platform's master key; this is a disclosed scope boundary (see the module docstring) marking exactly where a real KMS/HSM integration would plug in.

**Risk Engine** (`risk_engine/`) — dynamic risk scoring for 8 entity types (user, session, workflow, prompt, agent, tool, data, organization) with exponential half-life decay so stale risk fades rather than sticking around, factor-weighted score accumulation, and top-risky/history queries.

**Threat Detection** (`threat_detection/`) — nine detectors matching the platform's `ThreatType` taxonomy one-to-one: brute force, API abuse, tool abuse (rate/window heuristics), privilege escalation, credential abuse, suspicious workflow, malicious prompt (reuses the guardrail detectors), anomaly (z-score against a caller-supplied baseline), and behavior deviation (novelty detection against an established action baseline). Each fired detection persists a `ThreatDetectionModel` with a detected → investigating → confirmed/dismissed → mitigated lifecycle.

**AI Governance** (`governance/`) — a governed-asset registry (models, prompts, workflows, datasets, agents, knowledge bases) using the "own the pointer, not the data" pattern, forward-only lifecycle progression (draft → review → approved → production, with deprecated/retired reachable as a kill switch from any stage), and approval workflows with policy-driven required-approval counts that promote the asset's lifecycle stage on the final crossing approval.

**Security Events & Audit** (`events/`, `audit/`) — an append-only security events feed across 10 categories (authentication, authorization, policy/prompt/tool/workflow violations, secrets access, risk changes, threat detections, administrative actions) with retention sweeps, and a free-form immutable audit log (`action` is any caller-chosen dotted string — approval history, configuration/policy changes, model/tool usage, compliance evidence — rather than a fixed taxonomy).

**Compliance** (`compliance/`) — framework configuration (GDPR/SOC2/ISO27001/HIPAA-ready/custom), evidence collection against specific controls, retention policy configuration, legal holds that take precedence over retention-driven deletion, consent tracking with expiry, and data residency enforcement.

**Observability & Analytics** (`analytics/`) — read-only aggregation views over every module above: threat trends, guardrail/policy violation summaries, risk score distribution, combined security incident counts, compliance posture, secrets usage, encryption key status, and governance metrics.

## Concurrency

Three commit-spanning `asyncio.Lock` sequences, the same pattern established across every prior AIOS platform for check-then-act races that span multiple statements (separate callers own separate DB connections; SQLite only makes a write visible to others once committed):

- `GovernanceAssetService.register_asset` — idempotent-by-external-ref creation, locked per `tenant_id:asset_type:external_ref_id`.
- `ApprovalWorkflowService.record_decision` — approval-count threshold crossing, locked per `request_id`.
- `SecretService.rotate_secret` — version deactivate-then-create, locked per `secret_id`.

All three are proven under real concurrent load in `tests/performance/test_concurrency.py`, which races genuine independent DB connections via `asyncio.gather` (never the rollback-isolated test fixture) and asserts no duplicate rows, no lost approval votes, and no colliding secret version numbers.

## Testing

135 tests, 94% coverage, ruff clean. Real concurrency stress tests included. Test suite mirrors the module breakdown: `tests/policies`, `tests/guardrails`, `tests/pii`, `tests/dlp`, `tests/secrets`, `tests/encryption`, `tests/risk_engine`, `tests/threat_detection`, `tests/governance`, `tests/events`, `tests/audit`, `tests/compliance`, `tests/analytics`, `tests/sec_api` (11 end-to-end HTTP tests driving every domain through the real FastAPI app), `tests/performance` (concurrency stress), `tests/repository` (schema smoke test).

## Disclosed scope boundaries

Consistent with every prior AIOS platform's honest-gap posture:

- Guardrail and threat detectors are real, working regex/heuristic-pattern detection based on documented attack signatures — not trained ML classifiers.
- PII detection covers entity types with reliable regex signatures (email, phone, SSN, credit card, IP address); name/address/passport/bank-account/medical-record detection needs NER and isn't attempted.
- Structured output validation is a deliberate subset of JSON Schema (no `$ref`/`oneOf`/`anyOf`/`allOf`/`pattern`/`format`).
- Encryption key material is derived from a single master key rather than resolved against a real KMS/HSM — the `material_ref` indirection marks exactly where that integration point is.
- Anomaly detection is a z-score check against a caller-supplied baseline, not a trained model.

## Running it

```bash
pip install -r requirements.txt
uvicorn security_platform.sec_api.application_factory:create_app --factory --reload
```

Every request needs an `X-Tenant-Id` header; `X-User-Id` is optional (system-triggered checks legitimately have no human actor). Interactive docs at `/docs`.
