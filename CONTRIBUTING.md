# Contributing to AIOS

This repository is 21 independently deployable services (20 Python/FastAPI
backends + 1 Next.js frontend) sharing a common set of conventions. This
guide covers the conventions and workflow that apply across all of them;
each platform's own `README.md` covers its module-specific design notes.

## Repository layout

Each `aios-*` directory is a self-contained project with its own
`requirements.txt` (or `package.json`), tests, and README. Six backend
platforms (`aios-prompt-platform`, `aios-agent-platform`,
`aios-memory-platform`, `aios-workflow-engine`, `aios-tool-platform`,
`aios-evaluation-platform`) install `aios-ai-core` as an editable sibling
dependency (`-e ../aios-ai-core` in their `requirements.txt`), so they
expect to sit next to `aios-ai-core` on disk, exactly as they do in this
repository.

Root-level files (`docker-compose.yml`, `k8s/`, `docker/`) wire the
services together for local/staging use; they aren't part of any single
service.

## Backend conventions (Python / FastAPI)

Every backend service follows the same architecture — read an existing
platform's source before adding to another one, so new code matches:

- **Domain layer**: pure-Python entities with guarded state machines
  (illegal state transitions raise, they don't silently no-op).
- **Persistence**: SQLAlchemy 2.0 async ORM models, repositories, and a
  `RepositoryRegistry` unit-of-work — services never touch `Session`
  directly.
- **Service layer**: business logic, one class per bounded capability,
  constructed with its repositories/dependencies injected.
- **API layer**: FastAPI routers under `api/v1` (or the platform's
  equivalent `_api` package), built via an `create_app()` Application
  Factory — never a module-level `app = FastAPI()` global, so tests can
  build isolated instances with overridden dependencies.
- **Config**: a single `pydantic-settings` `Settings` class per platform,
  read via `get_settings()`. Never read `os.environ` directly outside that
  module.
- **Errors**: a per-platform exception hierarchy mapped to HTTP responses
  by FastAPI exception handlers — services raise domain exceptions, not
  `HTTPException`.

### Setup

```bash
cd aios-<platform>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m pytest
ruff check .
```

### Before opening a PR

- `ruff check .` must pass with no errors (`ruff format .` first if it
  reports formatting issues).
- `python3 -m pytest` must pass in full — don't skip or `xfail` a test to
  get green; fix it or explain why it's obsolete and remove it.
- New endpoints need a test exercising them through the FastAPI test
  client (`httpx.AsyncClient` against the real app), not just a service-
  layer unit test — the two catch different classes of bugs.
- If you add a new outbound HTTP call, give it an explicit timeout.
- If you touch startup/shutdown behavior, verify it against the platform's
  `lifespan` module — schema creation only runs for SQLite, and the engine
  must be disposed on shutdown.

## Frontend conventions (`aios-frontend`)

Next.js 14 App Router + TypeScript, Zustand for client state, Radix UI +
Tailwind for components.

```bash
cd aios-frontend
npm install
npm run dev
npm run typecheck && npm run lint && npm run test && npm run build
```

- Prefer Server Components by default; add `"use client"` only where
  interactivity requires it.
- **Never pass a function as a prop from a Server Component into a Client
  Component** — it isn't serializable across that boundary and will pass
  `next dev` but fail `next build`. If a Client Component needs
  caller-configurable formatting/behavior, accept a serializable
  discriminant (a string/enum) and resolve it to a function *inside* the
  Client Component — see `components/charts/trend-area-chart.tsx` for the
  pattern.
- Run `npm run build` (not just `npm run dev`) before considering frontend
  work done — `next build`'s static generation and RSC serialization
  checks catch real bugs `next dev` and `tsc --noEmit` don't.

## Commit hygiene

- Never commit `.env`, real credentials, or a filled-in
  `k8s/secrets.yaml`. `.env.example` files document required variables
  with placeholder values only.
- Keep commits scoped to one platform where possible — these are
  independently deployable services, and mixed-platform commits make
  history harder to bisect.

## Adding a new platform

Follow the existing 18 domain platforms as the template: same layering,
same `Settings`/`lifespan` pattern, same `/health`, `/health/live`,
`/health/ready` endpoints, a `Dockerfile` + `.dockerignore` matching the
sibling platforms' pattern (standalone vs. monorepo-context, depending on
whether it needs `aios-ai-core`), a `.github/workflows/ci.yml`, and an
entry in the root `docker-compose.yml` and `k8s/`.

## Shared modules and system checks

Two small cross-cutting modules are copied into every service, so each stays independently deployable:

- `<package>/<api>/edge_guard.py`: the internal-token and CORS policy every service installs in its app factory.
- `<package>/clock.py`: the service's only clock. Take every timestamp from `utc_now()` (ORM defaults already do);
  calling `datetime.now()` directly breaks ordering and can make durations negative.

Keep the copies byte-identical: `python scripts/check_shared_modules.py` (CI runs it) fails if one drifts.

Before opening a pull request that touches more than one service, run the whole system once:

```bash
python scripts/test_all.py        # every service's test suite
python scripts/dev.py             # in another terminal: all 20 services
python scripts/smoke_test.py      # readiness, write persistence, edge guard
```
