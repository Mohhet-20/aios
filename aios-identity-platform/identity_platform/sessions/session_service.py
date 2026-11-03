"""SessionService: the stateful half of authentication — creates,
rotates, and revokes `SessionModel` rows (keyed by a hashed refresh
token) and pairs each with a freshly minted JWT access token from
`JwtService`. Concurrent-session limits default to evicting the
oldest active session (matches common consumer-app UX, e.g. "you've
been signed out on another device"); pass `evict_oldest=False` to
instead raise `ConcurrentSessionLimitExceededError` and let the caller
decide (e.g. an enterprise admin policy that hard-caps sessions).

The read-count -> evict-oldest -> insert sequence in `create_session`
is a multi-step critical section that can't be reduced to a single
atomic SQL statement (unlike a plain quota check), so it is serialized
per-user via an in-process `asyncio.Lock`. This is the same
single-process-scope tradeoff already documented on `RateLimitService`:
correct for one process, an approximation once horizontally scaled
(a distributed lock, e.g. Redis-backed, would be the drop-in
replacement behind the same interface)."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from identity_platform.config.settings import Settings, get_settings
from identity_platform.core.exceptions import ConcurrentSessionLimitExceededError, SessionExpiredError, SessionRevokedError
from identity_platform.database.base import utcnow
from identity_platform.domain.entities import _aware
from identity_platform.models.session import SessionModel
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security.tokens import generate_raw_token, hash_token
from identity_platform.sessions.jwt_service import JwtService
from identity_platform.sessions.mappers import apply_session_domain_to_model, session_to_domain


@dataclass
class SessionIssueResult:
    session: SessionModel
    access_token: str
    raw_refresh_token: str


class SessionService:
    # Per-user locks, shared across all SessionService instances within
    # this process (keyed on user_id, not on `self`) so that two
    # SessionService objects created for the same request-handling
    # process still serialize against each other for the same user.
    _user_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None, jwt_service: JwtService | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self.jwt_service = jwt_service or JwtService(settings=self.settings)

    async def create_session(
        self, user_id: str, *, organization_id: str | None = None, ip_address: str | None = None,
        user_agent: str | None = None, device_fingerprint: str | None = None, evict_oldest: bool = True,
    ) -> SessionIssueResult:
        # The read-count -> evict-oldest -> insert sequence below is a
        # check-then-act critical section spanning multiple statements,
        # so concurrent calls for the *same* user must be serialized or
        # the concurrent-session limit can be oversold (verified via a
        # stress test before this lock was added). Different users
        # never contend for the same lock, so this doesn't serialize
        # unrelated traffic.
        #
        # The lock alone isn't sufficient: each caller typically owns its
        # own DB connection/transaction (one per request, via its own
        # `session_scope()`), and SQLite only makes a write visible to
        # *other* connections once it commits. If this method returned
        # and released the lock before committing, the next lock holder
        # could still read a stale, pre-commit active-session count from
        # its own transaction. So this commits the unit of work while
        # still holding the lock, guaranteeing the next waiter observes
        # this session's write. `create_session` is only ever called as
        # the sole write in its request (see identity_api/v1/sessions.py),
        # so committing here early doesn't truncate a larger transaction.
        async with self._user_locks[user_id]:
            active = await self.repos.sessions.list_active_for_user(user_id)
            if len(active) >= self.settings.max_concurrent_sessions_per_user:
                if not evict_oldest:
                    raise ConcurrentSessionLimitExceededError(
                        f"user '{user_id}' already has {len(active)} active sessions (limit {self.settings.max_concurrent_sessions_per_user})"
                    )
                oldest = min(active, key=lambda s: _aware(s.last_used_at))
                await self.revoke_session(oldest.id, reason="concurrent_session_limit_evicted")

            raw_refresh_token = generate_raw_token()
            session = SessionModel(
                user_id=user_id, organization_id=organization_id, refresh_token_hash=hash_token(raw_refresh_token),
                ip_address=ip_address, user_agent=user_agent, device_fingerprint=device_fingerprint,
                expires_at=utcnow() + timedelta(seconds=self.settings.jwt_refresh_token_ttl_seconds),
            )
            await self.repos.sessions.add(session)
            await self.repos.session.commit()

        access_token = self.jwt_service.issue_access_token(user_id=user_id, session_id=session.id, organization_id=organization_id)
        return SessionIssueResult(session=session, access_token=access_token, raw_refresh_token=raw_refresh_token)

    async def refresh(self, raw_refresh_token: str) -> SessionIssueResult:
        """Rotates the refresh token on every use (the old one is
        invalidated the instant a new one is issued) so a leaked,
        already-rotated refresh token is a dead end for an attacker."""
        session = await self.repos.sessions.get_by_refresh_token_hash(hash_token(raw_refresh_token))
        if session is None:
            raise SessionRevokedError("refresh token is invalid")
        if session.status == "revoked":
            raise SessionRevokedError(f"session '{session.id}' has been revoked")
        if session.status == "expired" or _aware(session.expires_at) < utcnow():
            entity = session_to_domain(session)
            if entity.status.value == "active":
                entity.expire()
                apply_session_domain_to_model(entity, session)
                await self.repos.sessions.update(session)
            raise SessionExpiredError(f"session '{session.id}' has expired")

        new_raw_refresh_token = generate_raw_token()
        session.refresh_token_hash = hash_token(new_raw_refresh_token)
        session.last_used_at = utcnow()
        session.expires_at = utcnow() + timedelta(seconds=self.settings.jwt_refresh_token_ttl_seconds)
        await self.repos.sessions.update(session)

        access_token = self.jwt_service.issue_access_token(
            user_id=session.user_id, session_id=session.id, organization_id=session.organization_id
        )
        return SessionIssueResult(session=session, access_token=access_token, raw_refresh_token=new_raw_refresh_token)

    async def revoke_session(self, session_id: str, *, reason: str = "user_logout") -> SessionModel:
        session = await self.repos.sessions.get_or_404(session_id)
        entity = session_to_domain(session)
        entity.revoke(reason=reason)
        apply_session_domain_to_model(entity, session)
        return await self.repos.sessions.update(session)

    async def revoke_all_for_user(self, user_id: str, *, reason: str = "revoke_all") -> int:
        active = await self.repos.sessions.list_active_for_user(user_id)
        for session in active:
            entity = session_to_domain(session)
            entity.revoke(reason=reason)
            apply_session_domain_to_model(entity, session)
            await self.repos.sessions.update(session)
        return len(active)

    async def list_active_for_user(self, user_id: str) -> list[SessionModel]:
        return await self.repos.sessions.list_active_for_user(user_id)

    async def sweep_expirations(self) -> list[SessionModel]:
        """Idempotent — safe to call on a timer. Returns sessions this
        sweep call actually transitioned to EXPIRED."""
        expired: list[SessionModel] = []
        for session in await self.repos.sessions.list_expired_active(older_than=utcnow()):
            entity = session_to_domain(session)
            entity.expire()
            apply_session_domain_to_model(entity, session)
            await self.repos.sessions.update(session)
            expired.append(session)
        return expired
