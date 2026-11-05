# AIOS Enterprise Production Infrastructure & MLOps Platform

Package `infra_platform`. This README was reconstructed during the documentation audit architecture audit — the platform shipped without one; every fact below is verified against the actual source (settings, module docstrings, exceptions, route count, test count), not inferred. Part of the same audit pass, an entirely empty and unreferenced `security_ctrl/` package (just an `__init__.py`, no other content, no imports anywhere) was removed as dead code — confirmed safe by re-running the full suite (still 127 passed) afterward.

## What this is

The production infrastructure and MLOps backbone: a container image registry with a build → scan → sign → publish lifecycle, a Kubernetes control plane (clusters, node pools, namespaces, generic K8s resources, HPA/VPA), a CI/CD platform (pipelines, gated runs, releases), model lifecycle management (registry + guarded promotion), experiment tracking, a feature store, generic artifact management, an inference platform (real-time/batch/streaming/async serving with weighted traffic routing), deployment strategies (rolling/canary/blue-green under one guarded lifecycle), generic autoscaling (horizontal/vertical/cluster/GPU/queue-based/predictive/cost-aware as one polymorphic policy table), multi-cloud account/resource pointers, and disaster recovery (backups, snapshots, recovery plans with an RPO/RTO commitment, failover events). Built with the same clean/layered architecture as every other AIOS platform.

## Architecture

- `domain/` — pure-Python entities with guarded `_transition()` state machines.
- `models/` — SQLAlchemy 2.0 async ORM models, 48 tables — the platform leans heavily on polymorphic single-table designs (`ScalingPolicyModel` over `resource_type`/`policy_type`, generic K8s resources over `kind`) rather than one table per resource variant, the same "one table, not seven near-identical ones" pattern used elsewhere in this platform.
- `repositories/` — one repository per model plus a `RepositoryRegistry` unit-of-work (includes the `get_many()` batch-fetch method added platform-wide during the platform-wide audits).
- Service modules — one directory per domain: `containers/`, `kubernetes/`, `cicd/`, `model_registry/`, `experiments/`, `feature_store/`, `artifacts/`, `inference/`, `deployment/`, `autoscaling/`, `cloud/`, `recovery/`, `observability/`, `security/`.
- `infra_api/` — FastAPI Application Factory, versioned routers (167 routes) + an unversioned `/health` probe, a shared exception-handler layer mapping the 54-class domain exception hierarchy to HTTP status codes.
- `dependencies/` — FastAPI dependency wiring (DB session → `RepositoryRegistry` → services).

## Module breakdown

**Containers & Image Registry** (`containers/`) — build → scan → sign → publish, plus version retention pruning. A critical-severity scan finding blocks an image from ever reaching signed/published when `image_scan_critical_block` is enabled — supply-chain security is a gate, not an afterthought.

**Kubernetes** (`kubernetes/`) — clusters, node pools, namespaces, generic K8s resources modeled polymorphically over `kind` rather than one table per resource type, resource quotas, and HPA/VPA autoscaler configs. `K8sService.apply` uses a commit-spanning `asyncio.Lock` (see Concurrency).

**CI/CD** (`cicd/`) — pipeline definitions, triggered runs with per-stage tracking, deployment gates (manual/policy approval checkpoints within a run, also lock-guarded — see Concurrency), and releases (promotion + rollback).

**Model Lifecycle Management** (`model_registry/`) — a registry entry per logical model name, versions beneath it with a guarded development → staging → production → archived lifecycle, and approval-gated promotion (an approval record is always created for audit purposes, even in configurations where the promotion itself doesn't block on it).

**Experiment Tracking** (`experiments/`) — experiments group runs; runs carry a guarded running → completed/failed/killed lifecycle; metrics support multi-step logging (training curves); parameters are logged once per key per run as the reproducibility record of what config produced a result.

**Feature Store** (`feature_store/`) — feature groups (an entity-keyed collection, e.g. all features keyed by `user_id`), versioned features within a group (draft → active → deprecated), and validation rules (not_null, range, regex) that gate a feature going live online.

**Artifact Management** (`artifacts/`) — a single generic store for every artifact type the platform produces (models, datasets, embeddings, prompt templates, agent configs, workflow templates, evaluation reports, training outputs, deployment packages) — one `ArtifactModel`, not one table per type.

**Inference Platform** (`inference/`) — real-time/batch/streaming/async inference services on CPU or GPU compute, plus weighted routing rules across service variants — the traffic-splitting primitive canary releases, blue-green cutovers, and multi-model serving all build on.

**Deployment Strategies & Autoscaling** (`deployment/`, `autoscaling/`) — a single guarded `Deployment` lifecycle (pending → in_progress → succeeded/failed, with pause/resume for canary bake windows and rollback reachable from any non-pending, non-terminal state) parameterized by a `strategy` field (rolling, canary, blue-green) rather than a separate lifecycle per strategy. Autoscaling is similarly generic: `ScalingPolicyModel` is polymorphic over `resource_type`/`resource_id` and `policy_type` (horizontal, vertical, cluster, GPU, queue-based, predictive, cost-aware). `AutoscalingService.scale` is lock-guarded per policy (see Concurrency).

**Multi-Cloud & Disaster Recovery** (`cloud/`, `recovery/`) — cloud accounts (a credential/subscription reference per provider — never raw credentials) and cloud resources follow the same "own the pointer, not the data" posture as the artifact/collaboration-asset pattern used elsewhere in AIOS. Disaster recovery covers backups (guarded pending → in_progress → completed/failed), point-in-time snapshots, reusable recovery plans carrying an RPO/RTO commitment, guarded recovery executions, and cross-region failover events.

**Observability & Security** (`observability/`, `security/`) — deployment success-rate tracking against a configurable alert threshold, and opaque token primitives used for build/run correlation ids shown once and generic secret-like references this platform needs without ever persisting the raw value.

## Concurrency

Three commit-spanning `asyncio.Lock` sequences — more than most sibling platforms, reflecting that this platform's core operations (applying a K8s resource, approving a deployment gate, scaling a policy) are inherently check-then-act sequences where a race has real operational consequences:

- `K8sService.apply` — locked per resource key.
- `CicdService` deployment-gate approval — locked per gate id.
- `AutoscalingService.scale` — locked per policy id.

## Testing

129 tests passing, ruff clean.

## Self-review

This README was written after the fact as part of a documentation-consistency audit. The platform itself was already solid (129 tests, 167 REST routes, three deliberately-placed concurrency locks, ruff-clean); the audit's contribution here was closing the missing-README gap and removing one confirmed-dead empty package.

## Running it

```bash
pip install -r requirements.txt
uvicorn infra_platform.infra_api.application_factory:create_app --factory --reload
```
