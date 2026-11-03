# AIOS Enterprise Authentication, Organizations & Multi-Tenant Platform

The identity layer every other AIOS subsystem sits on top of: a production-grade backend for authentication, organizations, teams, workspaces, projects, groups, RBAC, multi-tenancy, service accounts/API keys, security policy, and audit — the thing an AI Core, Prompt Platform, Agent Platform, Memory Platform, Workflow Engine, or Tool Platform call to answer "who is this, what org/tenant are they in, and are they allowed to do this."

This is Phase 11 of the AIOS build. Package `identity_platform`, table prefix `ip_`.

## What it does

**Users, credentials, and sessions.** A `User` carries account status through a real lifecycle (`PENDING_VERIFICATION` → `ACTIVE` ↔ `SUSPENDED` → `DEACTIVATED`), backed by password credentials hashed with stdlib `hashlib.pbkdf2_hmac` (format `pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>` — no bcrypt/passlib dependency), email verification and password-reset tokens, and magic-link login. `SessionModel` rows are keyed by a hashed refresh token, paired with short-lived JWT access tokens (`JwtService`), and support rotation-on-refresh (the old refresh token is dead the instant a new one is issued) and a per-user concurrent-session cap with either hard rejection or oldest-session eviction.

**MFA and device trust.** TOTP implemented from scratch against RFC 6238 (stdlib `hmac`/`hashlib`/`base64`/`struct`, no `pyotp`), with recovery codes (one-way hashed, single-use) and trusted-device records that let a known device skip a second factor for a bounded window. TOTP secrets are Fernet-encrypted at rest — genuinely reversible, unlike passwords/recovery codes/API keys, because the platform itself has to read the raw secret back to verify a 6-digit code — a distinction documented at the point of use, not left implicit.

**Federated identity.** `ExternalIdentityModel` links a user to an external provider (Google, Microsoft, Okta, GitHub, SAML, generic OIDC) by provider + subject, with a real link/unlink/find-or-create-on-login flow so a first-time SSO login provisions a user rather than requiring a pre-existing account.

**RBAC and fine-grained permissions.** Permission keys are `"<resource_type>:<action>"` strings, with `"<resource_type>:manage"` as a blanket per-resource-type grant and `"*"` as the superadmin wildcard. Roles are assigned at a scope (`SYSTEM`, `ORGANIZATION`, `WORKSPACE`, `TEAM`, `PROJECT`) and a `SYSTEM`-scope assignment authorizes globally regardless of what scope is being checked — an intentional "org admins can't accidentally out-rank a platform superadmin" property, not an oversight. A seed set of built-in roles (owner/admin/member/viewer, etc.) is idempotently provisioned via `seed_builtin_roles`.

**Organizations, workspaces, teams, projects, groups.** A five-level containment hierarchy (organization → workspace → team → project, plus cross-cutting groups) each with its own membership table and status lifecycle, invitations with accept/decline/expire, and department units for larger orgs. Every membership repository follows the same pattern: `list_active_for_*` never trusts a cached count, so quota checks can't drift from what's actually in the table.

**Multi-tenancy.** Organizations carry a `TenantTier` (FREE/PRO/ENTERPRISE) with quota presets (seats, workspaces, API keys) and tenant isolation helpers that scope every cross-entity query to a tenant boundary. Quota *usage* is always computed on demand from the real membership/resource tables — deliberately not cached in a separate metrics table, so it can never drift out of sync with reality the way a maintained counter can.

**Service accounts, API keys, webhooks.** Machine identities (`ServiceAccountModel`) get their own API keys, hashed the same one-way way as passwords, with scoped permissions, expiration, and revocation. Webhook signing secrets are Fernet-encrypted (reversible, like TOTP secrets, because the platform has to sign outgoing payloads with the raw secret).

**Security platform.** Password/session/MFA security policies per organization, a sliding-window in-process rate limiter (`RateLimitService`, explicitly documented as single-process-correct and an approximation once horizontally scaled — the same documented tradeoff the later session-concurrency fix relies on), risk scoring, and a security event log with resolve/unresolve tracking.

**Audit, compliance, governance.** An immutable `AuditLogEntry` per sensitive action (actor, action, resource, organization, metadata, timestamp), queryable by organization and filterable by action — the audit trail is what Task 145's bug fix (below) was caught by a test against.

**Observability.** Aggregate views over sessions, security events, and audit activity for admin dashboards, built the same on-demand-computation way as tenancy quota usage.

## Architecture

```
identity_platform/
  domain/                 entities.py (User, Session, Invitation, ApiKey, OrganizationMembership,
                           MfaFactor — pure-Python, guarded state machines) + enums.py (23 enums)
  models/                 SQLAlchemy ORM models, 32 tables (ip_ prefix) across users, sessions,
                           credentials, MFA, federated identity, RBAC, organizations, workspaces,
                           teams, projects, groups, memberships, invitations, API keys/service
                           accounts, security, governance
  repositories/           one repository per aggregate + RepositoryRegistry unit-of-work (~20
                           lazily-memoized repositories)
  database/                async SQLAlchemy 2.0 + aiosqlite, WAL/busy-timeout/NullPool pragmas,
                           session_scope() (commits/rolls back) vs get_db_session() (caller-managed)
  authentication/          registration, login, password reset, email verification, magic links
  sessions/                SessionService (issue/refresh/revoke), JwtService
  mfa/                     TOTP (RFC 6238 from scratch), recovery codes, trusted devices
  federated/               external identity link/unlink/find-or-create-on-login
  authorization/           RBAC: roles, permissions, role assignments, scope resolution
  organizations/           organizations, workspaces, teams, projects, groups, memberships,
                           invitations, departments
  tenancy/                 tenant tiers, quota presets, on-demand usage computation, isolation
  api_keys/                API keys, service accounts, webhook secrets
  security_platform/       security policies, rate limiting, risk scoring, security events
  governance/               audit log, compliance/retention
  observability/           session/security/audit aggregate views
  identity_api/            FastAPI routers (119 endpoints across 18 domains) + application factory
```

### Design decisions worth knowing about

**Two session helpers with different commit contracts, on purpose.** `session_scope()` commits on clean exit and rolls back on exception — used everywhere a caller wants normal request-scoped transaction semantics, including the API layer's dependency chain. `get_db_session()` neither commits nor rolls back, for callers (mainly tests) that want to manage their own transaction boundary explicitly. Task 147 caught that the API dependency chain had originally been wired to `get_db_session()`, which would have silently discarded every production write the moment a real client hit the API — fixed before it ever shipped, by switching the dependency to `session_scope()` and documenting the distinction on both functions so it can't be re-confused later.

**Never `return`/`break` out of `async for session in session_scope(): ...`.** This one cost real debugging time: calling `return` inside that loop closes the async generator via `GeneratorExit`, which does not resume execution after the `yield` — so the post-yield `await session.commit()` is silently skipped and nothing persists, while the test still reports green because assertions inside the loop see an in-memory, would-be-committed object. Confirmed with a standalone reproduction script before trusting any concurrency test result. Every stress test in `tests/performance/` captures its result in an outer variable and returns only after the loop completes naturally.

**Check-then-act races need different fixes depending on whether they reduce to one SQL statement.** The organization seat-quota race (`MembershipService.add_organization_member`) reduces cleanly: a naive "count active members, then insert if under quota" is two statements and provably oversells seats under concurrency (proven with both organic `asyncio.gather` load and a deterministic forced-barrier test before the fix, and again after — the *unsafe* naive path is kept as a permanent regression test alongside the fix). The fix is a single `INSERT ... SELECT ... WHERE (subquery)` statement — SQLite's per-statement write-lock guarantees the count-check and the insert happen as one atomic unit, with no other statement able to interleave. The concurrent-session-limit race (`SessionService.create_session`) does *not* reduce to one statement — evicting the oldest session is a conditional UPDATE that has to happen before the INSERT, based on a read that itself has to be current. That one is fixed with an in-process `asyncio.Lock` keyed per user, held across the read, evict, insert, *and* the commit — the lock has to span the commit specifically, because each caller owns its own DB connection and SQLite doesn't make one connection's write visible to another until it commits; a lock that released before commit (the first attempt) still let the next waiter start from a stale, pre-commit count. Both fixes are the smallest correct tool for their shape of race, not one fix pattern copy-pasted onto both.

**Reversible encryption is the exception, not the default.** Passwords, API keys, recovery codes, and refresh/access tokens are one-way SHA-256/PBKDF2 hashed — the platform never needs the raw value back. TOTP secrets and webhook signing secrets are Fernet-encrypted — the platform genuinely does need the raw value back (to compute a 6-digit code or sign an outgoing payload). Every place a secret is stored, the choice between the two is deliberate and stated in that module's docstring, not inferred from what happened to be convenient.

**Permission scope resolution has one deliberate escape hatch.** A `SYSTEM`-scope role assignment satisfies any authorization check regardless of the scope actually being checked (an org-scoped check, a workspace-scoped check, etc.) — because a platform superadmin needs to act everywhere without a role row in every single organization. Every other scope is checked strictly against the resource's actual containing scope.

## REST API

119 endpoints across 18 routers, all under `/api/v1`: auth (9 — register/login/verify/reset/magic-link), sessions (5 — create/refresh/revoke/revoke-all/list), MFA (9 — enroll/verify/challenge/recovery codes/trusted devices), federated (3 — link/unlink/login-via-provider), authorization (9 — roles/permissions/assignments/checks), organizations (10), workspaces (5), teams (4), projects (4), groups (5), memberships (12 — org/workspace/team/project/group membership CRUD), invitations (4), tenancy (2 — tier/quota usage), api_keys (12 — API keys + service accounts + webhook secrets), security (11 — policies/rate limits/risk/events), governance (7 — audit log queries), observability (7), and health (1). Caller identity travels via request context the same way every sibling AIOS platform's API layer assumes an authenticated gateway in front.

## Testing

181 tests, all passing, 92% line coverage: domain state-machine unit tests (15), a repository smoke test (4), and dedicated suites for authentication (15), sessions (10), MFA (6), federated identity (13), authorization/RBAC (16), organizations/workspaces/teams/projects/groups/memberships (17), tenancy (7), API keys & service accounts (12), security platform (20), governance/audit (6), observability (7), a full HTTP-level API suite (16, driving the platform purely through `httpx.AsyncClient` against the real FastAPI app), and a concurrency/stress suite (4).

The stress suite is deliberately adversarial rather than a happy-path smoke test: `test_naive_check_then_insert_is_provably_unsafe_under_a_forced_race` uses an `asyncio.Event`/`asyncio.Lock` barrier to force the worst-case interleaving and asserts the *unfixed* code path actually oversells seats (it does — proving the hazard was real, not theoretical), `test_atomic_seat_quota_insert_is_safe_under_the_same_forced_race` proves the fix holds under that identical forced interleaving, `test_concurrent_seat_quota_never_oversold` exercises the fix under organic `asyncio.gather` load, and `test_concurrent_session_creation_respects_limit_or_evicts_cleanly` fires 8 concurrent session-creation calls against a limit of 3 and asserts the final count never exceeds it. Three genuine, previously-undetected bugs were caught by these tests rather than by inspection: a query against a non-existent `resolved_at` column in `SecurityEventRepository.list_unresolved` (the real column is `resolved`), a query against a non-existent `event_type` column in `AuditLogEntryRepository.list_for_organization` (the real column is `action`), and the two concurrency races described above.

Run the suite:
```
python3 -m pytest -q
```

## Self-review

**Can this platform authenticate and authorize every other AIOS subsystem consistently?** Yes — every downstream platform in this build (AI Core, Prompt Platform, Agent Platform, Memory Platform, Workflow Engine, Tool Platform) already assumes an `X-User-Id`-style caller-identity header from an authenticated gateway; this platform is what issues and validates the credentials and sessions behind that header, and its RBAC permission-key format (`"<resource_type>:<action>"`) is generic enough that any of those platforms' resource types slot in without a schema change here.

**Can tenant boundaries actually be trusted?** Every organization-scoped repository query filters by organization/tenant id at the query level, not by post-filtering in application code, and quota usage is always computed live against the real membership tables rather than a cache that could silently drift from what a tenant is actually consuming. The one documented single-process caveat is `RateLimitService`, whose in-process sliding window is correct for one process and becomes an approximation once horizontally scaled — the same caveat pattern already established for this kind of component in earlier AIOS platforms, with a stated drop-in replacement path (a Redis-backed store) behind the same interface.

**Does RBAC hold up under real concurrent writes, not just sequential test calls?** This was tested directly rather than assumed: the seat-quota and concurrent-session-limit races were both found by writing genuine concurrent stress tests (not the rollback-isolated fixture used by the rest of the suite), confirmed as real bugs with concrete before/after evidence, and fixed at the root — one via a single atomic SQL statement, the other via a properly commit-spanning lock — with the unsafe path kept as a permanent regression test so the hazard can't silently return.

**Are secrets actually safe at rest?** No REST endpoint anywhere in `identity_api/` returns a decrypted secret, a raw password hash, or a raw API key after creation (API keys are shown once, at creation, the same as every real-world provider). One-way hashing is used everywhere the platform doesn't need the raw value back; Fernet encryption is used only where it genuinely does (TOTP verification, webhook signing), and that distinction is documented at each use site rather than left to be rediscovered.

**Can new organizations onboard at enterprise scale without schema changes?** Tenant tiers are data (`TenantTier` + quota presets), not code paths — a new tier or a new quota dimension is a preset entry, not a new branch in the services that enforce it. The five-level containment hierarchy (org → workspace → team → project, plus groups) and its membership tables are uniform across levels, so a new containment concept would extend the existing pattern rather than requiring a new one.

## What's explicitly out of scope (per this phase's scope boundary)

No Collaboration features, no Enterprise Analytics platform (Observability here covers session/security/audit aggregates only, not product analytics), and no MLOps — this is Authentication, Organizations & the Multi-Tenant Platform only, exactly as scoped.
