"""Append-only log of every CLI command a developer runs — the raw
material the Developer Analytics module aggregates into `cli_command`
usage events, and what `aios diagnostics` reads back to show a
developer their own recent command history."""
from __future__ import annotations

from developer_platform.models.cli import CliCommandLogModel
from developer_platform.repositories.registry import RepositoryRegistry


class CliCommandLogService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def log_command(
        self, tenant_id: str, *, session_id: str, command: str, args: dict | None = None, exit_code: int = 0,
    ) -> CliCommandLogModel:
        record = CliCommandLogModel(
            tenant_id=tenant_id, session_id=session_id, command=command, args=args or {}, exit_code=exit_code,
        )
        return await self.repos.cli_command_logs.add(record)

    async def list_for_session(self, tenant_id: str, session_id: str, *, limit: int = 200) -> list[CliCommandLogModel]:
        return await self.repos.cli_command_logs.list_for_session(tenant_id, session_id, limit=limit)
