"""CLI session lifecycle: `aios auth login` exchanges a long-lived API
key for a short-lived CLI session token (`cli_token_ttl_minutes`,
default 30 days), hashed at rest exactly like an API key. Status is a
simple field-based transition (active -> expired/revoked) guarded
directly here rather than through a dedicated domain entity — the same
"simpler status fields guarded in-service" precedent used for node
pools, deployment gates, and other lightly-stated resources in the
prior Infrastructure Platform."""
from __future__ import annotations

from datetime import timedelta

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import CliSessionExpiredError, CliNotAuthenticatedError
from developer_platform.database.base import utcnow
from developer_platform.domain.entities import _aware
from developer_platform.domain.enums import CliSessionStatus
from developer_platform.models.cli import CliSessionModel
from developer_platform.repositories.registry import RepositoryRegistry
from developer_platform.security.tokens import generate_raw_token, hash_token

_TRANSITIONS: dict[CliSessionStatus, set[CliSessionStatus]] = {
    CliSessionStatus.ACTIVE: {CliSessionStatus.EXPIRED, CliSessionStatus.REVOKED},
    CliSessionStatus.EXPIRED: set(),
    CliSessionStatus.REVOKED: set(),
}


def _transition(session: CliSessionModel, target: CliSessionStatus) -> None:
    current = CliSessionStatus(session.status)
    if target not in _TRANSITIONS.get(current, set()):
        raise CliSessionExpiredError(f"CLI session '{session.id}' cannot move from {current.value} to {target.value}")
    session.status = target.value


class CliSessionResult:
    def __init__(self, session: CliSessionModel, raw_token: str):
        self.session = session
        self.raw_token = raw_token


class CliSessionService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def start_session(self, tenant_id: str, *, developer_id: str) -> CliSessionResult:
        raw_token = generate_raw_token()
        session = CliSessionModel(
            tenant_id=tenant_id, developer_id=developer_id, token_hash=hash_token(raw_token),
            status=CliSessionStatus.ACTIVE.value,
            expires_at=utcnow() + timedelta(minutes=self.settings.cli_token_ttl_minutes),
        )
        session = await self.repos.cli_sessions.add(session)
        return CliSessionResult(session=session, raw_token=raw_token)

    async def verify_session(self, raw_token: str) -> CliSessionModel:
        session = await self.repos.cli_sessions.get_by_token_hash(hash_token(raw_token))
        if session is None:
            raise CliNotAuthenticatedError("CLI session token is invalid")
        if session.status == CliSessionStatus.REVOKED.value:
            raise CliNotAuthenticatedError(f"CLI session '{session.id}' has been revoked")
        if session.status == CliSessionStatus.EXPIRED.value or _aware(session.expires_at) < utcnow():
            if session.status != CliSessionStatus.EXPIRED.value:
                _transition(session, CliSessionStatus.EXPIRED)
                await self.repos.cli_sessions.update(session)
            raise CliSessionExpiredError(f"CLI session '{session.id}' has expired — run `aios auth login` again")

        session.last_seen_at = utcnow()
        return await self.repos.cli_sessions.update(session)

    async def revoke_session(self, session_id: str) -> CliSessionModel:
        session = await self.repos.cli_sessions.get_or_404(session_id)
        _transition(session, CliSessionStatus.REVOKED)
        return await self.repos.cli_sessions.update(session)

    async def list_for_developer(self, tenant_id: str, developer_id: str) -> list[CliSessionModel]:
        return await self.repos.cli_sessions.list_for_developer(tenant_id, developer_id)
