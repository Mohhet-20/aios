"""MCP session management: a client connects to a registered MCP
server for a bounded window (`mcp_session_ttl_minutes`) carrying a
declared permission set (e.g. `["resources.read", "tools.invoke"]`).
`check_permission` is the authorization gate every resource/tool/prompt
call would run through in a real transport implementation."""
from __future__ import annotations

from datetime import timedelta

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import McpPermissionDeniedError, McpSessionExpiredError, McpSessionNotFoundError, NotFoundError
from developer_platform.database.base import utcnow
from developer_platform.domain.entities import _aware
from developer_platform.domain.enums import McpSessionStatus
from developer_platform.models.mcp import McpSessionModel
from developer_platform.repositories.registry import RepositoryRegistry

_TRANSITIONS: dict[McpSessionStatus, set[McpSessionStatus]] = {
    McpSessionStatus.ACTIVE: {McpSessionStatus.EXPIRED, McpSessionStatus.CLOSED},
    McpSessionStatus.EXPIRED: set(),
    McpSessionStatus.CLOSED: set(),
}


def _transition(session: McpSessionModel, target: McpSessionStatus) -> None:
    current = McpSessionStatus(session.status)
    if target not in _TRANSITIONS.get(current, set()):
        raise McpSessionExpiredError(f"MCP session '{session.id}' cannot move from {current.value} to {target.value}")
    session.status = target.value


class McpSessionService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def start_session(
        self, tenant_id: str, *, mcp_server_id: str, client_id: str, permissions: list[str] | None = None,
    ) -> McpSessionModel:
        session = McpSessionModel(
            tenant_id=tenant_id, mcp_server_id=mcp_server_id, client_id=client_id,
            status=McpSessionStatus.ACTIVE.value, permissions=permissions or [],
            started_at=utcnow(), expires_at=utcnow() + timedelta(minutes=self.settings.mcp_session_ttl_minutes),
        )
        return await self.repos.mcp_sessions.add(session)

    async def touch_session(self, tenant_id: str, session_id: str) -> McpSessionModel:
        session = await self._get_or_404(tenant_id, session_id)
        if session.status != McpSessionStatus.ACTIVE.value:
            raise McpSessionExpiredError(f"MCP session '{session.id}' is not active")
        if _aware(session.expires_at) < utcnow():
            _transition(session, McpSessionStatus.EXPIRED)
            await self.repos.mcp_sessions.update(session)
            raise McpSessionExpiredError(f"MCP session '{session.id}' has expired")
        session.last_activity_at = utcnow()
        return await self.repos.mcp_sessions.update(session)

    async def close_session(self, tenant_id: str, session_id: str) -> McpSessionModel:
        session = await self._get_or_404(tenant_id, session_id)
        _transition(session, McpSessionStatus.CLOSED)
        return await self.repos.mcp_sessions.update(session)

    async def check_permission(self, tenant_id: str, session_id: str, required: str) -> None:
        session = await self.touch_session(tenant_id, session_id)
        if "*" in session.permissions or required in session.permissions:
            return
        raise McpPermissionDeniedError(f"MCP session '{session.id}' lacks permission '{required}'")

    async def list_active(self, tenant_id: str) -> list[McpSessionModel]:
        return await self.repos.mcp_sessions.list_active(tenant_id)

    async def list_for_server(self, tenant_id: str, mcp_server_id: str) -> list[McpSessionModel]:
        return await self.repos.mcp_sessions.list_for_server(tenant_id, mcp_server_id)

    async def _get_or_404(self, tenant_id: str, session_id: str) -> McpSessionModel:
        try:
            session = await self.repos.mcp_sessions.get_or_404(session_id)
        except NotFoundError as exc:
            raise McpSessionNotFoundError(f"MCP session '{session_id}' not found") from exc
        if session.tenant_id != tenant_id:
            raise McpSessionNotFoundError(f"MCP session '{session_id}' not found for tenant '{tenant_id}'")
        return session
